import base64
import webbrowser
from flask import Blueprint, flash, jsonify, render_template, request, redirect, send_file, send_from_directory, url_for
from flask_login import login_required, current_user
import natsort
import os
import shutil

from .db_utility import commit_current_user_details, get_current_path_details, get_current_course_details, commit_current_course_details, \
    commit_current_path_details, get_current_user_details
from .os_utility import check_code_present, create_dir, delete_dir, load_topics, load_toc_if_exist, build_toc_render_items, \
    load_folder, build_folder_structure_for_monaco_sidebar

main = Blueprint('main', __name__)
root_course_dir = os.getenv('course_dir', '.')
OS_ROOT = os.path.join(os.path.expanduser('~'), 'EducativeViewer')


@main.route('/')
def index():
    return render_template('index.html')


'''
Endpoint to load the course list directory
'''
@main.route('/courses', methods=['GET', 'POST'])
@login_required
def courses():
    highlight_idx = None
    last_visited_topic = ""
    last_visited_index = 0
    
    current_path_details = get_current_path_details(current_user.username)
    course_dir = current_path_details.last_visited_directory if current_path_details else root_course_dir
    last_visited_course = current_path_details.last_visited_course if current_path_details else ""
    
    temp_folder_path = os.path.join(OS_ROOT, "temp", current_user.username)
    delete_dir(temp_folder_path)

    download_button_color = '#ed4444 !important'
    current_user_details = get_current_user_details(current_user.username)
    if current_user_details.downloadaccess:
        download_button_color = '#82f382 !important'

    target_folder = request.args.get("folder") or request.form.get("folder")
    go_back = "back" in request.args or "back" in request.form
    
    if target_folder:
        new_course_dir = os.path.join(course_dir, target_folder)
        
        # 1. Standalone HTML check
        if os.path.isfile(new_course_dir):
            if target_folder.endswith(".html"):
                commit_current_course_details(username=current_user.username,
                                              last_visited_course=course_dir.split(os.path.sep)[-1],
                                              last_visited_topic=target_folder,
                                              last_visited_index=0)
                return redirect(url_for('main.topics', topics=target_folder))
            else:
                # Other browser-openable files (PDF, image, text, etc.)
                return redirect(url_for('main.view_file', filename=target_folder))

        # 2. Directory check
        if os.path.isdir(new_course_dir):
            course_dir = new_course_dir
            last_visited_course = course_dir.split(os.path.sep)[-1]
            
            # Check if this folder is actually a topic (contains its own name as .html)
            if os.path.isfile(os.path.join(course_dir, target_folder + ".html")):
                return redirect(url_for('main.topics', topics=target_folder))
            
            # Otherwise, traverse inside
            commit_current_path_details(username=current_user.username,
                                        last_visited_directory=course_dir,
                                        last_visited_course=last_visited_course)

    elif go_back:
        if len(root_course_dir) < len(course_dir):
            course_dir = os.path.sep.join(course_dir.split(os.path.sep)[:-1])
            last_visited_course = course_dir.split(os.path.sep)[-1]
            commit_current_path_details(username=current_user.username, 
                                        last_visited_directory=course_dir,
                                        last_visited_course=last_visited_course)
            print(f"DEBUG: back to='{course_dir}'")

    # Render logic
    folders = natsort.natsorted(load_folder(course_dir))
    folder = os.path.split(course_dir)[-1]
    
    current_course_details = get_current_course_details(current_user.username, last_visited_course)
    if current_course_details:
        last_visited_topic = current_course_details.last_visited_topic
        if last_visited_topic in folders:
            highlight_idx = folders.index(last_visited_topic)

    toc = load_toc_if_exist(course_dir)
    if toc:
        toc_items = build_toc_render_items(toc, highlight_idx)
        return render_template("courses_toc.html", toc_items=toc_items, folder=folder, download_button_color=download_button_color)
    
    return render_template("courses.html", folder_list=folders, folder=folder, highlight_idx=highlight_idx, download_button_color=download_button_color)


'''
Endpoint to load topics.
'''
@main.route("/courses/<topics>", methods=['GET', 'POST'])
@login_required
def topics(topics):
    from urllib.parse import unquote
    topics = unquote(topics)
    current_path_details = get_current_path_details(current_user.username)
    course_dir = current_path_details.last_visited_directory
    last_visited_course = current_path_details.last_visited_course
    current_course_details = get_current_course_details(current_user.username, last_visited_course)
    
    toc = load_toc_if_exist(course_dir)
    topic_folders = natsort.natsorted(load_topics(course_dir))
    
    print(f"DEBUG: topics='{topics}'")
    print(f"DEBUG: course_dir='{course_dir}'")
    print(f"DEBUG: topic_folders count={len(topic_folders)}")
    
    # Determine the iteration index (itr)
    itr = current_course_details.last_visited_index if current_course_details else 0
    
    if toc:
        # For TOC-based courses, use the existing topics_toc logic
        return topics_toc(topics, course_dir, toc, itr)
        
    # Find the index of the current topic in the folder list
    if topics in topic_folders:
        itr = topic_folders.index(topics)
        print(f"DEBUG: Exact match found at index {itr}")
    else:
        # Try a more fuzzy match to handle encoding quirks
        import difflib
        matches = difflib.get_close_matches(topics, topic_folders, n=1, cutoff=0.6)
        if matches:
            itr = topic_folders.index(matches[0])
            print(f"DEBUG: Fuzzy match found: '{matches[0]}' at index {itr}")
        else:
            print(f"DEBUG: No match found for '{topics}'. Falling back to index {itr}")
            if itr >= len(topic_folders):
                itr = 0

    if request.method == "POST":
        print(f"DEBUG: POST topics='{topics}', form={request.form.to_dict()}, itr={itr}")
        if request.form.get("code_filesystem"):
            path = f"file:///{course_dir}/{topic_folders[itr]}".replace("\\", "/")
            webbrowser.open(path)
            # Stay on the same page after opening in file system
            return redirect(url_for('main.topics', topics=topics))
        
        # Fallback redirect if some other POST occurs
        return redirect(url_for('main.topics', topics=topic_folders[itr]))

    if not topic_folders:
        return redirect(url_for('main.courses'))

    # Ensure index is within bounds
    itr = max(0, min(itr, len(topic_folders) - 1))
    current_topic = topic_folders[itr]

    # Save the state correctly
    commit_current_course_details(username=current_user.username,
                                  last_visited_course=last_visited_course,
                                  last_visited_topic=current_topic,
                                  last_visited_index=itr)

    template_folder = "/".join(course_dir[len(root_course_dir) + 1:].split(os.path.sep))
    if current_topic.endswith(".html"):
        webpage = f"{template_folder}/{current_topic}"
    else:
        webpage = f"{template_folder}/{current_topic}/{current_topic}.html"
    
    is_code_present = not current_topic.endswith(".html") and check_code_present(course_dir, current_topic)
    
    # Detect if it's a media file that should be shown in an iframe
    media_extensions = ('.pdf', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.mp3')
    is_media = current_topic.lower().endswith(media_extensions)
    
    rendered_html = render_template(
        "topics.html", code_present=is_code_present, webpage=webpage, folder=f"{current_topic}",
        folder_list=topic_folders, itr=itr, is_media=is_media, current_topic=current_topic)
    return rendered_html


'''
Method to load the toc contained topics
'''
def topics_toc(topics, course_dir, toc, itr):
    from urllib.parse import unquote
    topics = unquote(topics)
    toc_items = build_toc_render_items(toc)
    print(f"DEBUG: topics_toc topics='{topics}', itr_start={itr}")
    try:
        itr = next(i for i, toc_item in enumerate(toc_items) if toc_item['title'] == topics)
        print(f"DEBUG: TOC match found at index {itr}")
    except StopIteration:
        print(f"DEBUG: No TOC match found for '{topics}'")
        pass
    if request.method == "POST":
        print(f"DEBUG: topics_toc POST topics='{topics}', form={request.form.to_dict()}, itr={itr}")
        if request.form.get("code_filesystem"):
            path = f"file:///{course_dir}/{toc_items[itr]['title']}".replace("\\", "/")
            webbrowser.open(path)
            return redirect(url_for('main.topics', topics=topics))
        
        # Fallback redirect
        return redirect(url_for('main.topics', topics=toc_items[itr]['title']))

    '''
    GET request, this is used to refresh the webpage if required    
    '''
    last_visited_course = course_dir.split(os.path.sep)[-1]
    commit_current_course_details(username=current_user.username,
                                  last_visited_course=last_visited_course,
                                  last_visited_topic=toc_items[itr]['title'],
                                  last_visited_index=itr)

    template_folder = "/".join(course_dir[len(root_course_dir) + 1:].split(os.path.sep))
    topic_item = toc_items[itr]['title']
    if topic_item.endswith(".html"):
        webpage = f"{template_folder}/{topic_item}"
    else:
        webpage = f"{template_folder}/{topic_item}/{topic_item}.html"
    
    is_code_present = check_code_present(course_dir, topic_item) if not topic_item.endswith(".html") else False
    
    # Detect if it's a media file
    media_extensions = ('.pdf', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.mp3')
    is_media = topic_item.lower().endswith(media_extensions)

    rendered_html = render_template(
        "topics_toc.html", code_present=is_code_present, webpage=webpage, folder=f"{topic_item}",
        toc_items=toc_items, itr=itr, is_media=is_media, current_topic=topic_item)
    return rendered_html


'''
Endpoint to load the code/quiz files in monaco editor
'''
@main.route("/courses/code/<codes>", methods=['GET', 'POST'])
@login_required
def codes(codes):
    current_path_details = get_current_path_details(current_user.username)
    course_dir = current_path_details.last_visited_directory
    directory_path = os.path.join(course_dir, codes)
    encoded_path = base64.b64encode(directory_path.encode()).decode()
    return render_template("monaco-editor.html", encoded_path=encoded_path)


'''
Endpoint to list all the files in monaco-sidebar
'''
@main.route('/courses/list-files')
@login_required
def list_files():
    encoded_path = request.args.get('encoded_path')
    directory_path = base64.b64decode(encoded_path.encode()).decode()
    files = build_folder_structure_for_monaco_sidebar(directory_path, directory_path)
    return jsonify(files)


'''
Endpoint to load file-content in monaco-editor
'''
@main.route('/courses/file-content/<path:filename>')
@login_required
def file_content(filename):
    encoded_path = request.args.get('encoded_path')
    directory_path = base64.b64decode(encoded_path.encode()).decode()
    filename = base64.b64decode(filename.encode()).decode()
    file_path = os.path.join(directory_path, filename)
    return send_file(file_path)


'''
Endpoint to download the folder as zip
'''
@main.route('/courses/download/<folder>', methods=['POST', 'GET'])
@login_required
def download(folder):
    course_dir = root_course_dir
    current_path_details = get_current_path_details(current_user.username)
    if current_path_details is not None:
        course_dir = current_path_details.last_visited_directory
        
    if request.method == "POST":
        if not current_user.downloadaccess:
            return render_template("downloadaccess.html")
        '''
        Copy the course directory to temp folder and zip it
        '''
        temp_folder_path = os.path.join(OS_ROOT, "temp", current_user.username, folder)
        delete_dir(temp_folder_path)
        create_dir(temp_folder_path)
        temp_folder_course_dir = os.path.join(temp_folder_path, folder)
        shutil.copytree(course_dir, temp_folder_course_dir)
        shutil.make_archive(temp_folder_course_dir, 'zip', temp_folder_course_dir)
        return redirect(url_for('main.courses') + f"/tmp/{folder}/{folder}.zip")
    return redirect(url_for('main.courses'))


@main.route("/courses/view_file/<path:filename>")
@login_required
def view_file(filename):
    current_path_details = get_current_path_details(current_user.username)
    course_dir = current_path_details.last_visited_directory if current_path_details else root_course_dir
    return send_from_directory(course_dir, filename)


@main.route("/courses/tmp/<path:filepath>", methods=['POST', 'GET'])
@login_required
def file_download(filepath):
    temp_folder_path = os.path.join(OS_ROOT, "temp", current_user.username)
    try:
        return send_from_directory(temp_folder_path, filepath, as_attachment=True)
    except:
        return render_template("404.html", message="File does not exist")
    

@main.route("/courses/getdownloadaccess", methods=['POST', 'GET'])
@login_required
def getdownloadacess():
    current_user_details = get_current_user_details(current_user.username)
    message = ''
    if request.method == "POST":
        downloadtoken = request.form.get('downloadtoken')
        if downloadtoken == os.getenv('downloadtoken', ''):
            current_user_details.downloadaccess = True
            commit_current_user_details(current_user_details)
            return redirect(url_for('main.courses'))
        else:
            message = 'Please enter correct Download Token and try again.'
    return render_template("downloadaccess.html", message=message)
    

@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', message="Page does not exist"), 404
