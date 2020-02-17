import os, uuid
from glob import glob
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


def input_connect_string():
	 connect_str = input("Please input connection string! \n"
		"This can be found in the storage account portal interface\n"
		 "in the left Settings-bar under Acess keys\n")

	 os.environ['AZURE_STORAGE_CONNECTION_STRING'] = connect_str 


def upload_dir_content_to_container(local_folder_name, container_name, file_types=""):
    ##Upload from local to storage account:
    ##file_types is to filter folder for certain types fx. ".png" 

    assert local_folder_name in os.listdir(),\
        "local_folder_name must be in working directory"

    if not os.getenv('AZURE_STORAGE_CONNECTION_STRING'): input_connect_string()

    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    local_folder_content = glob(f"{local_folder_name}/*{file_types}")
    #for all images to be uploaded
    for local_file_name in local_folder_content:
        short_local_file_name = local_file_name.split("/")[-1]
        #Get a reference to a BlobClient object by calling 
        #the get_blob_client method on the BlobServiceClient 
        #from the Create a container section.
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=short_local_file_name)

        with open(local_file_name, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)


def download_txt_content_from_container(container_name, local_folder_name):
    # Download text files from container_name to local_folder_name
    
    assert local_folder_name in os.listdir(),\
        "local_folder_name must be in working directory"

    if not os.getenv('AZURE_STORAGE_CONNECTION_STRING'): input_connect_string()

    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    
    #List names of all files in cloud container
    container_client = blob_service_client.get_container_client(container_name)
    cloud_blob_content = [f.name for f in container_client.list_blobs()]
    
    #For all files to possibly be downloaded
    for cloud_file_name in cloud_blob_content:
        short_cloud_file_name = cloud_file_name.split("/")[-1]
        
        if short_cloud_file_name.split(".")[-1] == "txt":
            #Get a reference to a BlobClient object by calling 
            #the get_blob_client method on the BlobServiceClient 
            #from the Create a container section.
            blob_client = blob_service_client.get_blob_client(
                    container=container_name, blob=short_cloud_file_name)

            download_path = f"{local_folder_name}/{short_cloud_file_name}"

            with open(download_path, "w+") as download_file:
                content = blob_client.download_blob().readall()
                download_file.write(str(content))
        else:
            pass

print("This")