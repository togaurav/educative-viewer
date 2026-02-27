import base64
import glob
import json
import os
import shutil


def delete_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)

def create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def check_code_present(course_dir, topic):
    topic_path = os.path.join(course_dir, topic)
    if not os.path.isdir(topic_path):
        return False
    # If it's a topic folder, it usually has more than just the index .html/.htm file
    if len(os.listdir(topic_path)) > 1:
        return True
    return False


def load_topics(course_dir):
    topics = []
    browser_extensions = {'.html', '.htm', '.pdf', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.mp3', '.m4v', '.avi', '.mkv', '.wmv'}
    for item in os.listdir(course_dir):
        if item.startswith(".") or item.startswith("__"):
            continue
        item_path = os.path.join(course_dir, item)
        if os.path.isdir(item_path):
            # Check for name.html or name.htm
            if os.path.isfile(os.path.join(item_path, item + ".html")) or \
               os.path.isfile(os.path.join(item_path, item + ".htm")):
                topics.append(item)
        else:
            _, ext = os.path.splitext(item)
            if ext.lower() in browser_extensions:
                topics.append(item)
    return topics


def load_toc_if_exist(course_dir):
    toc = None
    if course_dir:
        toc_path = os.path.join(course_dir, "__toc__.json")
        if os.path.exists(toc_path):
            with open(toc_path) as toc_file:
                toc = json.load(toc_file)
    return toc


def load_folder(course_dir):
    items = []
    # Extensions that can typically be opened/previewed in a browser
    browser_extensions = {'.html', '.htm', '.pdf', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.mp3', '.m4v', '.avi', '.mkv', '.wmv'}
    for item in os.listdir(course_dir):
        if item.startswith(".") or item.startswith("__"):
            continue
        item_path = os.path.join(course_dir, item)
        if os.path.isdir(item_path):
            items.append(item)
        else:
            _, ext = os.path.splitext(item)
            if ext.lower() in browser_extensions:
                items.append(item)
    return items


def build_toc_render_items(toc, highlight_idx=0):
    toc_items = []
    curr_topic_idx = 0
    for item in toc["toc"]:
        if type(item) is dict:  # category
            toc_items.append({"title": item["category"], "is_category": True, "color": "white", "focus": ""})
            for topic in item["topics"]:
                temp_map = {"title": topic[1], "is_category": False, "color": "white", "focus": ""}
                if curr_topic_idx == highlight_idx:
                    temp_map["color"] = "#0dfd10"
                    temp_map["focus"] = "focus-button"
                toc_items.append(temp_map)
                curr_topic_idx += 1
        else:  # assessments, projects, cloud labs..
            temp_map = {"title": item[1], "is_category": False, "color": "white", "focus" : ""}
            if curr_topic_idx == highlight_idx:
                temp_map["color"] = "#0dfd10"
                temp_map["focus"] = "focus-button"
            toc_items.append(temp_map)
            curr_topic_idx += 1
    return toc_items


def build_folder_structure_for_monaco_sidebar(directory, root):
    structure = []

    for item in glob.glob(os.path.join(directory, '*')):
        if os.path.isdir(item):
            folder_name = os.path.basename(item)
            node = {"text": folder_name, "nodes": []}

            # Recursively build structure for subfolder
            substructure = build_folder_structure_for_monaco_sidebar(item, root)
            if substructure:
                node["nodes"].extend(substructure)

            structure.append(node)
        elif os.path.isfile(item):
            filename = os.path.basename(item)
            if filename != f"{os.path.splitext(filename)[0]}.html":
                file_path = os.path.join(directory, filename)
                file_path = os.path.relpath(file_path, root)
                encoded_path = base64.b64encode(file_path.encode()).decode()
                structure.append({"text": filename, "type": "file", "encoded_path": encoded_path})

    return structure
