from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery

import os
import dotenv
from history import History

dotenv.load_dotenv()

llm_client = AzureOpenAI(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_API_ENDPOINT"),
)

search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY")),
)


def find_documents(query):
    embedding = (
        llm_client.embeddings.create(
            input=query, model=os.getenv("AZURE_OPENAI_API_EMBEDDER_NAME")
        )
        .data[0]
        .embedding
    )
    vector_query = VectorizedQuery(vector=embedding, fields="content_vector")
    results = search_client.search(search_text=query, vector_queries=[vector_query])
    documents = []
    count = 0
    for result in results:
        count += 1
        documents.append(
            {
                "id": result["id"],
                "content": result["content"],
                "score": result["@search.score"],
            }
        )

    documents = sorted(documents, key=lambda x: x["score"], reverse=True)
    return documents


def generate_context(documents):
    context = ""
    context_length = 0
    for document in documents:
        adding_length = len(document["content"])
        if context_length + adding_length > 7350:
            continue

        context += document["content"] + "\n"
        context_length += adding_length

    return context


def complete_chat(history, human_message, context):
    history.add_system_prompt()
    history.add_system_message(context)
    history.add_system_message(
        "Reminder: Only answer questions related to Erasmushogeschool Brussel."
    )
    history.add_user_message(human_message)
    result = llm_client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME"),
        messages=history.raw_history(),
        max_tokens=512,
    )
    history.add_assistant_message(
        result.model_dump()["choices"][0]["message"]["content"]
    )
    return history


def generate_context_prompt(context):
    if context == "":
        return "No additional context found, refuse to answer the user's question politely."
    else:
        return (
            "Based on this context answer the user's question if it is inside of your domain: "
            + context
        )


app = Flask(__name__)
CORS(app)

history = History()


@app.route("/chat", methods=["POST"])
@cross_origin()
def new_message():
    global history
    human_message = request.get_json()["userMessage"]
    documents = find_documents(human_message)
    context = generate_context(documents)
    context_prompt = generate_context_prompt(context)
    history = complete_chat(history, human_message, context_prompt)
    return jsonify(history.filter_history())


@app.route("/chat", methods=["GET"])
@cross_origin()
def get_history():
    global history
    filtered_history = history.filter_history()
    return jsonify(filtered_history)


if __name__ == "__main__":
    history.add_assistant_message(
        "Hello, I am an AI assistant of Erasmushogeschool Brussel. How can I help you?"
    )
    app.run(host="0.0.0.0", port=5000, debug=True)
