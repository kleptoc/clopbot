import time #for sleeping
import praw #for reddit api
import json #for parsing repsonses from various websites
import urllib #for stuff
import requests #for getting APIs
import base64 #for imgur upload
import sys #for file stuff
import _thread #for threading

from bs4 import BeautifulSoup #for parsing sites
from time import gmtime, strftime #for debug output

error_wait_time = 60*1 #time before retry on error

subredd = sys.argv[1] #get subbreddit name from command line
#usernme = sys.argv[2] #get username from command line
#passwrd = sys.argv[3] #get password from command line
usernme = "BOT USERNAME HERE"
passwrd = "BOT PASSWORD HERE"
try:
  debugen = sys.argv[4] #get debug, if enabled (disables checking comments)
except:
  debugen = False

r = praw.Reddit(user_agent='clopbot by kleptoc') #start praw, with useragent
r.login(usernme, passwrd) #log into reddit

already_done = [] #list of items already done (probably a memory leak)

def clean_done(): #remove old items
  while len(already_done) > 50: #if list greater than 50 items
    already_done.pop(0) #remove the item

def curr_time(): #get current time for debug output
  return "[" + strftime("%H:%M:%S", gmtime()) + "] "

def print_out(message, submission=''): #debug output (time, subreddit, submission id, message)
  string = curr_time();
  string += "[" + subredd + "] "
  if not submission == '':
    string += "[" + submission.id + "] "
  string += message
  print(string)

def save_done(): #save completed items into a file
  clean_done()
  try:
    done_save_string = ""
    for done in already_done:
      if not done == "":
        done_save_string += done + ";"

    done_save_string = done_save_string[:-1]

    save_file = open(subredd+'_completed.txt', 'w')
    save_file.write(done_save_string)
    save_file.close()
  except:
    print_out("error saving!")

def load_done(): #load completed items into list
  try:
    save_file = open(subredd+'_completed.txt', 'r').read()
    save_file = save_file.split(';')

    for save in save_file:
      already_done.append(save)
  except:
    print_out("error loading!")

def post_comment(submission, url, extra=''): #post the comment
  print_out("posting comment", submission)
  comment = "[imgur mirror]("+url['data']['link']+")"
  if not extra == "": #I don't even know what this is for
    comment += "\n\nextra"
  comment += "\n\n^^This ^^comment ^^was ^^generated ^^by ^^a ^^bot ^^hastily ^^copied ^^from ^^the ^^dead ^^code ^^of ^^an ^^older ^^bot. ^^It's ^^being ^^managed ^^by [^^this ^^guy](http://www.reddit.com/u/kleptoc)"
  comment += "\n\n^^More ^^features ^^coming ^^soon ^^^^hopefully..."

  success = False
  while not success:
    try:
      submission.add_comment(comment)
      success = True
    except:
      print_out("error posting comment, wating to retry", submission)
      time.sleep(error_wait_time)

def upload_to_imgur(image, submission): #upload a file to imgur
  api_endpoint = 'https://api.imgur.com/3/upload.json'
  headers = {'Authorization': 'Client-ID CLIENT ID GOES HERE'}
  #needs an imgur api key

  success = False
  while not success:
    try:
      dl = requests.get(image)
      success = True
    except:
      print_out("error downloading image, waiting to retry", submission)
      time.sleep(error_wait_time)

  image = base64.b64encode(dl.content)

  success = False
  while not success:
    try:
      r = requests.post(api_endpoint, data={'image': image}, headers=headers, verify=False)
      success = True
    except:
      print_out("error POSTing data to imgur, waiting to retry", submission)
      time.sleep(error_wait_time)

  return r.text

def upload_and_comment(url, submission, extra=''): #download an image, then upload to imgur and comment it
  imgur = upload_to_imgur(url, submission)
  imgur = json.loads(imgur)
  if imgur['success'] == True:
    post_comment(submission, imgur, extra)
  else:
    print_out("imgur upload failed for " + url, submission)

def handle_e621(url, submission): #handle e621
  print_out('loading e621', submission)
  url = url.split('/')
  url = url[5]

  if '.png' in url or '.jpg' in url or '.jpeg' in url: #prevents inaccuracy in sample stuff
    try:
      test_type(url, submission)
      return
    except:
      print_out("error uploading e621")

  success = False
  tries = 0
  while not success:
    if tries == 5:
      print_out("failed because e621 didn't load", submission)
      return

    try:
      r = requests.get("http://e621.net/post/show/" + url + ".json")
      success = True
    except:
      print_out("error reading e621 API, waiting to retry", submission)
      time.sleep(error_wait_time)
      tries = tries + 1

  data = r.json()
  upload_and_comment(data['file_url'], submission)

def handle_fa(url, submission): #load furaffinity
  print_out("loading fa", submission)
  cookies = {'b': 'COOKIE_B', 'a': 'COOKIE_A'} #cookies never expire :P
  if "view" in url:
    url =  url.replace("view", "full")

  success = False
  while not success:
    try:
      r = requests.get(url, cookies=cookies)
      success = True
    except:
      print_out("error loading fa, waiting to retry", submission)
      time.sleep(error_wait_time)

  parse = BeautifulSoup(r.text)
  image = parse.find_all(id='submissionImg', limit=1)
  upload_and_comment('http:' + image[0]['src'], submission)

def handle_da(url, submission): #handle da
  print_out("loading da", submission)

  success = False
  while not success:
    try:
      data = urllib.urlopen("http://backend.deviantart.com/oembed?url=" + urllib.quote(submission.url))
      success = True
    except:
      print_out("error reading da API, waiting to retry", submission)
      time.sleep(error_wait_time)

  data = json.loads(data.read())
  upload_and_comment(data['url'], submission)

def handle_tumblr(url, submission): #handle tumblr
  print_out("loading tumblr", submission)

  blog_name = url.replace("http://", "")
  temp = blog_name.split("/")
  blog_name = temp[0]
  post_id = temp[2]

  api_url = "http://api.tumblr.com/v2/blog/%s/posts/photo?id=%s&api_key=API KEY HERE" % (blog_name, post_id)

  success = False
  while not success:
    try:
      r = requests.get(api_url)
      r = r.json()
      success = True
    except:
      print_out("error loading tumblr, waiting to retry", submission)
      time.sleep(error_wait_time)

  upload_and_comment(r['response']['posts'][0]['photos'][0]['alt_sizes'][0]['url'], submission)

def test_type(url, submission): #check if a site is an image
  print_out("checking if image", submission)

  success = False
  times = 0
  while times == 5 and not success:
    try:
      r = requests.head(url)
      headers = r.headers['content-type']

      if headers == "image/gif" or headers == "image/jpeg" or headers == "image/png" or headers == "image/tiff":
        imgur = upload_to_imgur(url, submission)
        imgur = json.loads(imgur)
        if imgur['success'] == True:
          post_comment(submission, imgur)
        else:
          print_out("imgur upload failed for " + url, submission)
      else:
        print_out("not image", submission)

      success = True

      times = times + 1
    except:
      print_out("error testing file type, waiting to retry", submission)
      time.sleep(error_wait_time)

def handle_derpi(url, submission): #handle derpibooru
  url = url.split("?")[0]

  success = False
  while not success:
    try:
      r = requests.get(url+".json")
      r = r.json()
      success = True
    except:
      print_out("error loading derpi, waiting to retry", submission)
      time.sleep(error_wait_time)

  upload_and_comment("http:"+r['image'], submission)

def get_inkbunny_sid(): #gets the sid for inkbunny
  success = False
  while not success:
    try:
      r = requests.get("https://inkbunny.net/api_login.php?username=USERNAME&password=PASSWORD")
      r = r.json()
    
      return r['sid']
    except:
      print_out("error getting inkbunny sid, waiting to retry")
      time.sleep(error_wait_time)

def handle_inkbunny(url, submission): #load an inkbunny page
  print_out("loading inkbunny", submission)

  success = False
  while not success:
    try:
      sid = get_inkbunny_sid()
      if "submissionview.php" in url:
        url = url.split("?id=")[1]
        r = requests.get("https://inkbunny.net/api_submissions.php?sid=" + sid + "&submission_ids=" + url)
        r = r.json()

        file_url = r['submissions'][0]['files'][0]['file_url_full']
        file_type = r['submissions'][0]['files'][0]['mimetype']

        if file_type == "image/gif" or file_type == "image/jpeg" or file_type == "image/png" or file_type == "image/tiff":
          upload_and_comment(file_url+"?sid="+sid, submission)
      else:
        r = requests.head(url)
        headers = r.headers['content-type']

        if headers == "image/gif" or headers == "image/jpeg" or headers == "image/png" or headers == "image/tiff":
          upload_and_comment(url+"?sid="+sid, submission)
        else:
          print_out("inkbunny not image")
      success = True
    except:
      print_out("error loading inkbunny, waiting to retry")
      time.sleep(error_wait_time)

def has_not_posted(submission): #check if comment already exists
  if debugen:
    return True

  success = False
  while not success:
    try:
      for comment in submission.comments:
        if str(comment.author).lower() == usernme.lower():
          return False
      return True
      success = True
    except:
      print_out("error checking comments, waiting to retry", submission)
      time.sleep(60*10)

def fetch_comments(): #load comments from page (function for error handling)
  success = False
  while not success:
    try:
      hot = r.get_subreddit(subredd).get_new(limit=50)
      return hot
    except:
      print_out("error fetching comments, waiting to retry")
      print_out(sys.exc_info()[0])
      time.sleep(60*10)

def runthread(submission): #basically what calls everything
  if has_not_posted(submission):
    if submission.domain == "e621.net":
      handle_e621(submission.url, submission)
    elif submission.domain == "furaffinity.net":
      handle_fa(submission.url, submission)
    elif "tumblr" in submission.domain:
      handle_tumblr(submission.url, submission)
    elif "inkbunny" in submission.domain:
      handle_inkbunny(submission.url, submission)
    elif "derpibooru" in submission.domain:
      handle_derpi(submission.url, submission)
    elif not submission.domain == "imgur.com":
      if not submission.domain == "i.imgur.com":
        test_type(submission.url, submission)
    

if not debugen: #don't load already completed things if in debug mode
  load_done()

print('Welcome! Loading ' + subredd + ' on user ' + usernme)
while True: #run thread
  try:
    for submission in fetch_comments():
      if submission.id not in already_done:
        print_out("reading", submission)
        _thread.start_new_thread(runthread, (submission,))
        already_done.append(submission.id)
    save_done()
    time.sleep(1800)
  except KeyboardInterrupt:
    save_done()
    print_out("good bye!")
    sys.exit(1)
  except:
    print_out("error doing something, waiting to retry")
    time.sleep(error_wait_time)