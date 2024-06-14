from azure.storage.blob import BlobServiceClient
from langchain.docstore.document import Document
from langchain_community.document_transformers import BeautifulSoupTransformer
from nltk.tokenize import sent_tokenize
import os
import dotenv

dotenv.load_dotenv()

def parse_html(html):
    document = [Document(page_content=html)]
    bs_transformer = BeautifulSoupTransformer()
    doc_transformed = bs_transformer.transform_documents(
        document,
        tags_to_extract=["span", "table", "li", "d", "h1", "h2", "h3", "h4", "h5", "p"],
        unwanted_tags=["a"],
    )[0]
    return doc_transformed.page_content


def chunk_text(text):
    chunks = []
    sentences = sent_tokenize(text)
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) > 512:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += sentence + " "
    if current_chunk != "":
        chunks.append(current_chunk)
    return chunks


def parse_file(path):
    with open(path, "r") as f:
        content = parse_html(f.read())
        chunks = chunk_text(content)
        return chunks


def parse_files(directory):
    files = []
    for filename in os.listdir(directory):
        print("Parsing file: " + filename)
        content = parse_file(directory + "/" + filename)
        files.append(content)
    return files


def clear_storage(container_client):
    blob_list = container_client.list_blobs()
    for blob in blob_list:
        container_client.delete_blob(blob.name)
        print(f"Deleted blob: {blob.name}")


def upload_files(container_client, file_paths):
    for file_path in file_paths:
        blob_name = os.path.basename(file_path)
        blob_client = container_client.get_blob_client(blob_name)

        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
            print(f"Uploaded file: {file_path}")


def main():
    print("Parsing files...")
    files = parse_files("./raw")
    print("Writing data to file...")
    if os.path.exists("./prepared"):
        for file in os.listdir("./prepared"):
            os.remove(f"./prepared/{file}")
        os.rmdir("./prepared")
    os.mkdir("./prepared")
    for i, chunks in enumerate(files):
        for j, chunk in enumerate(chunks):
            with open(f"./prepared/{i}-{j}.txt", "w") as f:
                f.write(chunk)
                # Replace with your connection string
    # Initialize BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(
        os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    )
    container_client = blob_service_client.get_container_client(
        os.getenv("AZURE_STORAGE_CONTAINER")
    )
    clear_storage(container_client)
    upload_files(
        container_client, [f"./prepared/{file}" for file in os.listdir("./prepared")]
    )


if __name__ == "__main__":
    main()
