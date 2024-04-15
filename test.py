import sys
import subprocess
import os
import shutil
from time import sleep
from playwright.sync_api import sync_playwright, expect
import sqlite3

BASE_DIR = "actividad0"

class bcolors:
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def clone_project(url, folder_name):
    result = subprocess.run(f"git clone {url} {folder_name}", shell=True)

    return result.returncode == 0

def list_commits():
    subprocess.run(f"PAGER=cat git log --oneline", shell=True, cwd=BASE_DIR)

def find_folder_with_file(path, file_name):
    files = os.listdir(path)

    for f in files:
        if f.startswith('.'):
            continue

        if f == file_name:
            return path

        full_path = os.path.join(path, f)

        if os.path.isdir(full_path):
            find_path = find_folder_with_file(full_path, file_name)
            if find_path is not None:
                return find_path

    return None

def migrate(manage_folder):
    subprocess.run("python manage.py migrate", cwd=manage_folder, shell=True)

def run_seed(manage_folder):
    con = sqlite3.connect(os.path.join(manage_folder, "db.sqlite3"))
    cur = con.cursor()
    cur.execute("""
        INSERT INTO polls_question(id, question_text, pub_date)
        VALUES(1, "What's app?", date());
    """)

    cur.execute("""
        INSERT INTO polls_choice(id, choice_text, votes, question_id)
        VALUES
            (1, "Nothing", 0, 1),
            (2, "Just checking in", 0, 1);
    """)

    con.commit()
    con.close()

def runserver(manage_folder):
    p = subprocess.Popen(
        "python manage.py runserver",
        shell=True,
        cwd=manage_folder
    )
    sleep(3)
    return p

def test():
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=False, slow_mo=500)
        context = browser.new_context()
        page = context.new_page()

        run_test("should list all polls", test_should_list_the_polls, page)
        run_test("should vote", test_should_vote, page)
         
        browser.close()

def run_test(name, test, page):
    try:
        test(page)
        print(bcolors.OKGREEN + f"[ok] {name}" + bcolors.ENDC)
    except Exception as inst:
        print(bcolors.FAIL + f"[fail] {name}" + bcolors.ENDC)
        print(inst)

def test_should_list_the_polls(page):
    page.goto("http://localhost:8000/polls")

    poll_list = page.get_by_role("list")
    expect(poll_list).to_be_visible()

    first_poll = page.get_by_role("listitem").nth(0)
    expect(first_poll).to_be_visible()

def test_should_vote(page):
    page.goto("http://localhost:8000/polls")
    link = page.get_by_role("link").nth(0)
    href = link.evaluate("link => link.href")

    chunks = href.split("/")
    chunks.reverse()

    poll_id = chunks[1]

    page.goto(f"http://localhost:8000/polls/{poll_id}/results")

    before_votes = (
        page
            .get_by_role("listitem")
            .nth(1)
            .evaluate("choice => /\d+/.exec(choice.textContent.trim())[0]")
    )

    page.goto(f"http://localhost:8000/polls/{poll_id}")
    page.get_by_role('radio').nth(1).click()
    page.get_by_role('button').click()

    after_votes = (
        page
            .get_by_role("listitem")
            .nth(1)
            .evaluate("choice => /\d+/.exec(choice.textContent.trim())[0]")
    )

    assert int(before_votes) + 1 == int(after_votes)

def main():
    url = sys.argv[1]

    result = clone_project(url, BASE_DIR)

    if result:
        list_commits()

        manage_folder = find_folder_with_file(BASE_DIR, "manage.py")

        if manage_folder is None:
            print("manage.py not found")
        else:
            db_folder = find_folder_with_file(BASE_DIR, "db.sqlite3")

            if db_folder is None:
                migrate(manage_folder)
                run_seed(manage_folder)
        
            server = runserver(manage_folder)
            test()
            server.kill()

        shutil.rmtree(BASE_DIR)


if __name__ == '__main__':
    main()

