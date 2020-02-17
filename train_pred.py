from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateEntry
from azure.cognitiveservices.vision.customvision.prediction import CustomVisionPredictionClient
from sklearn.metrics import classification_report
from glob import glob

import numpy as np
import os, time, shutil

def prompt_txt(resource):
    return( f"As found by clicking on the {resource} ressource found here: \n" 
            "https://www.customvision.ai/projects#/settings\n"
            "Or go through the portal to the ressource"
            "and find the key in left bar under 'Keys and Endpoint'\n")

def prompt_resource_id():
    os.environ["CVRESOURCEID"] = input("Please insert the Recouse Id of the prediction ressource\n "+ prompt_txt("prediction"))
def prompt_training_key():
    os.environ["CVTRAININGKEY"] = input("Please insert Training key \n" + prompt_txt("training"))
def prompt_enpoint_url():
    os.environ["CVENDPOINT"] = input("Please insert Enpoint url\n" + prompt_txt("training or prediction"))
def prompt_prediction_key():
    os.environ["CVPREDICTIONKEY"] = input("Please insert Prediction key \n" + prompt_txt("prediction"))


def delete_all_unpublished_projects():
    if not os.getenv("CVTRAININGKEY"): prompt_training_key()
    if not os.getenv("CVENDPOINT"): prompt_enpoint_url()
        
    training_api_key = os.getenv("CVTRAININGKEY")
    endpoint = os.getenv("CVENDPOINT")

    trainer = CustomVisionTrainingClient(training_api_key, endpoint)
    bol = input("delete all projects? - yes/no")
    if bol == "yes":
        for p in trainer.get_projects():
            try:
                trainer.delete_project(p.id)
                print(f"deletion of project {p.name} returned: succes\n")
            except Exception as e: 
                print(f"deletion of project {p.name} returned: {e}\n")
        print("DONE!")
    else: print("ABORTED!")

def append_to_image_list(image_folder, project, image_list, trainer, file_types="", total_img=None):
    
    files = glob(f"{image_folder}/*{file_types}")
    tag_name = image_folder.split("/")[-1]
    tag = trainer.create_tag(project.id, tag_name)
    #Generate ImageFiles from the files in the image_folder
    #The tag names will be that of the directory name 
    for fpath in files:
        fname = fpath.split("/")[-1]
        with open(fpath, "rb") as f:
            im = ImageFileCreateEntry(name=fname, contents=f.read(), 
                                 tag_ids=[tag.id])
            image_list.append(im)
            if total_img:
                percent_ImageFiles_created = int(len(image_list)/total_img*100)
                print(f"percent of ImageFiles created: {percent_ImageFiles_created}%", end="\r", flush=True)
                
    return(image_list)

def upload_check(upload_result, i, z):
    if upload_result.is_batch_successful:
        print(f"Upload image batch with images {i} to {z} Succes.")
    else:
        print(f"Upload of some images from batch with images {i} to {z} Failed.")
        print("\n    ----    Faulty Images:   ----")
        for q, image in enumerate(upload_result.images):
            if image.status != "OK": print(f"Image status of image nr {q}: {image.status}") 
        print("    ----     ----    ----    ----\n")

def create_and_train(project_name, paths_to_class_seperated_folders, file_types="", iteration_name=None ):
    #OBS! Elements in paths_to_class_seperated_folders can't end with '/'
    
    assert type(paths_to_class_seperated_folders) == list,\
        "paths_to_class_seperated_folders must be list of directory" +\
        "paths to the folders conatining the different image classes"
    
    instantiated_trianing_client = False
    while not instantiated_trianing_client:
        try:
            if not os.getenv("CVTRAININGKEY"): prompt_training_key()
            if not os.getenv("CVENDPOINT"): prompt_enpoint_url()
            training_api_key = os.getenv("CVTRAININGKEY")
            endpoint = os.getenv("CVENDPOINT")
            trainer = CustomVisionTrainingClient(training_api_key, endpoint)
            exsisting_projects = [p.name for p in trainer.get_projects()]
            instantiated_trianing_client = True

        except Exception as e:
            if "Endpoint" in str(e):
                print(e)
                print("The endpoint seems to be wrong. Please try again")
                prompt_enpoint_url()
            elif "Operation returned an invalid status code 'Access Denied'" in str(e):
                print(e)
                print("The training key seems to be wrong. Please try again")
                prompt_training_key()
            else:
                print(e)

    
    
    assert project_name not in exsisting_projects,\
        "projects already exists use function load_and_update_instead\n" +\
        "Or use delete_all_unpublished_projects() or select a new name to create project"
    
    print(f"Creating project with project name: {project_name}", flush=True)
    project = trainer.create_project(project_name)

    print("Converting images to Azure ImageFiles", flush=True)
    #To visualize process progress
    total_img = 0
    for image_folder in paths_to_class_seperated_folders:
         total_img += len(glob(f"{image_folder}/*{file_types}"))
            
    image_list = []
    for image_folder in paths_to_class_seperated_folders:
        
        append_to_image_list(image_folder, project, image_list, trainer, 
                             file_types=file_types, total_img=total_img)
    
    i = 0
    while i < len(image_list):
        z = (i+63)
        upload_result = trainer.create_images_from_files(project.id, images=image_list[i:z])
        upload_check(upload_result, i, z)
        i = z+1

    print("Training...", flush=True)
    iteration = trainer.train_project(project.id)
    #trainer.get_iteration_performance() TODO: performance feedback
    i = 0
    while (iteration.status != "Completed"):
        iteration = trainer.get_iteration(project.id, iteration.id)
        print(f"Training status: {iteration.status}{i * '.'}", end="\r", flush=True)
        time.sleep(1)
        i+=1
    
    if iteration_name or input("\npublish iteration? y/n") == "y":
               
        published = False
        while not published:
            try:
                if not iteration_name: iteration_name = input("under what name?")
                if not os.getenv("CVRESOURCEID"): prompt_resource_id()
                prediction_resource_id = os.getenv("CVRESOURCEID")
                trainer.publish_iteration(project.id, iteration.id, 
                    iteration_name, prediction_resource_id)
                published = True
            except Exception as e:
                if "Invalid prediction resource id" in str(e):
                    print(e)
                    print("Please try again")
                    prompt_resource_id()
                else:
                    print(e)

        print(f"published with itteration name: {iteration_name}")
                
        
def load_project_and_iterations(project_name):
    if not os.getenv("CVTRAININGKEY"): prompt_training_key()
    if not os.getenv("CVENDPOINT"): prompt_enpoint_url()

    training_api_key = os.getenv("CVTRAININGKEY")
    endpoint = os.getenv("CVENDPOINT")
    
    trainer = CustomVisionTrainingClient(training_api_key, endpoint)
    project_names = {p.name:p.id for p in trainer.get_projects()}
    project_id = project_names[project_name]
    
    project = trainer.get_project(project_id)
    iterations = trainer.get_iterations(project_id)
    
    return(project, iterations)

def choose_iteration(iterations):

    for i, itter in enumerate(iterations):
        print(i, "    |", itter.name)
        print("      |", itter.last_modified)
        print("___________________")
    
    iteration_nr = input("please choose iteration number\n"
                             "as written in the left index above\n")
    iteration_nr = int(iteration_nr)
    
    return(iterations[iteration_nr].name)

def rename_prediction_images(folder_to_predict):
    #This function expects a folder per class in folder_to_predict
    #with the class name as the folder name
    #TODO: find en måde at vær sikker på at mapperne har samme navn som de trænede klasser
    for root, dirs, files in os.walk(folder_to_predict):
        for d in dirs:
            for path in os.listdir(f"{folder_to_predict}/{d}"):
                pn = path.split(".")
                pn.insert(-1, d)
                new_path = f"{folder_to_predict}/{'.'.join(pn)}"  
                old_path = f"{folder_to_predict}/{d}/{path}" 
                try: 
                    shutil.copyfile(old_path, new_path) 
                    print(f"copied file: {old_path} --> {new_path}")   
                # If source and destination are same 
                except shutil.SameFileError: 
                    print("Source and destination represents the same file.") 
                # If destination is a directory. 
                except IsADirectoryError: 
                    print("Destination is a directory.") 
                # If there is any permission issue 
                except PermissionError: 
                    print("Permission denied.") 
                # For other errors 
                except: 
                    print("Error occurred while copying file.") 

def predict(image_folder, project_name, published_name=None, iteration_name=None, 
    file_types="", threshold = 0.5, visualize=False):
    if not os.getenv("CVPREDICTIONKEY"): prompt_prediction_key()
    if not os.getenv("CVENDPOINT"): prompt_enpoint_url()

    prediction_key = os.getenv("CVPREDICTIONKEY")
    endpoint = os.getenv("CVENDPOINT")
    predictor = CustomVisionPredictionClient(prediction_key, endpoint=endpoint)
    
    project, iterations = load_project_and_iterations(project_name)
    if not published_name:
        if not iteration_name: iteration_name = input("what is the iteration name?\n")
        published_name = iteration_name #choose_iteration(iterations) #TODO: Find way of fetching iterations
    
    files = glob(f"{image_folder}/*{file_types}")
    #nameing convention of the prediction images must be that of <id>.<class tag>.<file type>
    #f.eks 24a.bebyggelse.png TODO: overvej at lave en funktion, der laver en ny folder med disse
    #navene udfra to foldere af prediction images med class tag som folder navn

    prediction_objects_dict = {}
    labels_dict = {}

    nfiles =  len(files)
    for fpath in files:
        label = fpath.split("/")[-1].split(".")[-2]
        with open(fpath, "rb") as image_contents:
            image_data = image_contents.read()
            result = predictor.classify_image(project.id, published_name, image_data)
            prediction_objects_dict[fpath] = result
            labels_dict[fpath] = label
            # Display the results.
            print(f"percent done: {int((len(prediction_objects_dict)/nfiles)*100)} %", end="\r")

    #return(prediction_objects_dict, labels_dict) #TODO: REWRITE TO OOP AND SAVE THESE TO OBJECT
    

    predictions = list()
    labels = list()
    #Get prediction with highest probability - Apply threshold - and lookup label
    for name, predict_object in prediction_objects_dict.items():
        all_classes_pred_touple = [(p.tag_name, p.probability) for p in predict_object.predictions]
        highest_prob_pred_touple =  max(all_classes_pred_touple, key=lambda x: x[1])
        if highest_prob_pred_touple[1] > threshold:
            pred = highest_prob_pred_touple[0]
            label = labels_dict[name]
            predictions.append(pred)
            labels.append(label)

    n_uncertain = nfiles - len(predictions)


    #prnt result and then save as dict
    for bol in [False, True]:
        report = classification_report(labels, predictions, zero_division=0, 
            output_dict=bol) #TODO: save to object
        if not bol: print(f"\n {report} \n Predictions under threshold: {n_uncertain/nfiles}%") 

    
    return(labels, predictions, report, prediction_objects_dict, labels_dict)
    

predict("this", "that")
