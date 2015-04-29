#!/bin/python3

api_key = ""

download_dir = "torrents"
download_temp = "incomplete"
torrent_dir = "torrents"

delete_stopped_and_complete = True

#external_script = ""

use_aria = True
aria_executable = "aria2c"

API_URL = "https://api.justseed.it"

import os
import xml.dom.minidom
import shutil
import sys
import logging
import time
try:
    import urllib.request as urllib2
except:
    import urllib2

from subprocess import call
from urllib.error import HTTPError
from urllib.request import Request, urlopen, urlretrieve
import urllib


def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)


def getURLX(URL,data,retries=3,wait_time=1000):
    for i in range(0,retries):
        req = urllib.request.Request(URL,urllib.parse.urlencode(data).encode('utf-8'))
        x = xml.dom.minidom.parse(urllib.request.urlopen(req))
        status = x.getElementsByTagName("status")[0]
        if status and status.firstChild.data=="SUCCESS":
            return x
        print("Failed to load URL")
        time.sleep(wait_time)
    return None

def getFirstData(xml, tag):
    element = xml.getElementsByTagName(tag)[0]
    if element and element.hasChildNodes():
       return element.firstChild.data
    return ""

def urlProgress(blocks, blockSize, totalSize):
  try:
    if sys.version() < '3':
      print("%dMB/%dMB  Rate=%.1fMB/s ---- %2.1f%%        \r " % ((blocks*blockSize)/(1024*1024),(totalSize)/(1024*1024),float(blocks*blockSize)/(1024*1024*(time.time()-time_start)),(float(blocks*blockSize)/float(totalSize))*100)),
    else:
      print("%dMB/%dMB  Rate=%.1fMB/s ---- %2.1f%%         " % ((blocks*blockSize)/(1024*1024),(totalSize)/(1024*1024),float(blocks*blockSize)/(1024*1024*(time.time()-time_start)),(float(blocks*blockSize)/float(totalSize))*100),end="\r")
  except:
    return

time_start=0
def downloadTorrentFiles():
    global time_start
    print("Downloading")
    torrent_list = getURLX(API_URL + "/torrents/list.csp",{"api_key":api_key})
    if (torrent_list):
        for hash in torrent_list.getElementsByTagName("info_hash"):
            info_hash = hash.firstChild.data
            torrent_info = getURLX(API_URL + "/torrent/information.csp", {"api_key":api_key,"info_hash":info_hash})
            if (torrent_info):
                torrent_data = torrent_info.getElementsByTagName("data")[0]
                if float(getFirstData(torrent_data,"percentage_as_decimal")) > 99.99:
                    torrent_name = urllib.parse.unquote(getFirstData(torrent_data,"name"))
                    torrent_label = urllib.parse.unquote(getFirstData(torrent_data,"label"))
                    torrent_status = getFirstData(torrent_data,"status")
                    torrent_links = getURLX(API_URL + "/torrent/links/list.csp",{"api_key":api_key,"info_hash":info_hash})
                    if (torrent_links):
                        if (int(getFirstData(torrent_links,"total_links"))>0):
                            temp_path = os.path.join(download_temp,torrent_name)
                            if not os.path.exists(temp_path):
                                os.makedirs(temp_path)
                            if os.path.isdir(temp_path):
                                for row in torrent_links.getElementsByTagName("row"):
                                    filename = os.path.normpath(urllib.parse.unquote(getFirstData(row,"path")))
                                    url = urllib.parse.unquote(getFirstData(row,"url"))
                                    dir = os.path.join(temp_path,os.path.dirname(filename))
                                    if dir and not os.path.exists(dir):
                                        os.makedirs(dir)
                                    #download(url,os.path.join(temp_ath,filename))
                                    print("Downloading: " + filename)
                                    if use_aria:
                                      call([aria_executable,'-x5','-c','-d',temp_path,'-o',filename,url])
                                    else:
                                      time_start=time.time()
                                      urlretrieve(url,os.path.join(temp_path,filename),urlProgress)
                                if getURLX(API_URL + "/torrent/links/delete.csp",{"api_key":api_key,"info_hash":info_hash}):
                                    print("Deleted Links for "+torrent_name)
                                if torrent_label:
                                    download_path = download_dir.replace("[label]",torrent_label)
                                else:
                                    download_path  = download_dir.replace("[label]"+os.path.sep,"")
                                if not os.path.exists(download_path):
                                    os.makedirs(download_path)
                                if os.path.isdir(download_path):
                                    try:
                                        print(" Moving Completed Download.")
                                        shutil.move(temp_path,download_path)
                                    except:
                                        print("Error moving file!")
                                else:
                                    print("Error creating directory!")
                                #call(["python",external_script,download_path])

def cleanUpTorrents():
    print("Cleaning Up")
    torrent_list = getURLX(API_URL + "/torrents/list.csp",{"api_key":api_key})
    if (torrent_list):
        for hash in torrent_list.getElementsByTagName("info_hash"):
            info_hash = hash.firstChild.data
            torrent_info = getURLX(API_URL + "/torrent/information.csp", {"api_key":api_key,"info_hash":info_hash})
            if (torrent_info.getElementsByTagName("status")[0].firstChild.data == "SUCCESS"):
                if float(torrent_info.getElementsByTagName("percentage_as_decimal")[0].firstChild.data) > 99.99:
                    torrent_data = torrent_info.getElementsByTagName("data")[0]
                    if (getFirstData(torrent_data,"status") == "stopped"):
                        getURLX(API_URL + "/torrent/delete.csp",{"api_key":api_key,"info_hash":info_hash})
 

def uploadTorrents():
    print("Uploading")
    for file in os.listdir(torrent_dir):
        file_path = os.path.join(torrent_dir,file)

        if os.path.isdir(file_path):
            for f in os.listdir(file_path):
                if f.endswith(".torrent"):
                    print("Uploading torrent: " + f + " with label: " + file)
                    uploadTorrent(os.path.join(file_path,f),file)
                    os.rename(os.path.join(file_path,f),os.path.join(torrent_dir,file,f.replace(".torrent",".torrent.bak")))

        if file.endswith(".torrent"):
            print("Uploading torrent: " + file)
            uploadTorrent(file_path)
            os.rename(file_path,os.path.join(torrent_dir,file.replace(".torrent",".torrent.bak")))

def uploadTorrent(file_path,label=""):
    try:
        f = open(file_path,'rb')
        torrent_data = f.read()
    except IOError:
        print("Could not open file: " + file_path)
        return
    #Default naming uses the filename, let's use the name of the torrent file instead (might be more accurate)
    torrent_name = os.path.splitext(os.path.basename(file_path))[0]
    torrent_add = getURLX(API_URL + "/torrent/add.csp", {"api_key":api_key,"torrent_file": torrent_data,"prevent_auto_start":1})
    f.close()
    if torrent_add:
        info_hash = torrent_add.getElementsByTagName("info_hash")[0].firstChild.data
        getURLX(API_URL + "/torrent/set_auto_generate_links.csp", {"api_key":api_key,"info_hash":info_hash,"enable":True})
        getURLX(API_URL + "/torrent/set_name.csp", {"api_key":api_key,"info_hash":info_hash,"name":torrent_name})
        if label:
            getURLX(API_URL + "/torrent/set_label.csp", {"api_key":api_key,"info_hash":info_hash,"label":label})
        getURLX(API_URL + "/torrent/start.csp", {"api_key":api_key,"info_hash":info_hash})
                                    


#if not (os.path.isdir(download_dir)):
#    os.makedirs(download_dir)
if not (os.path.isdir(download_temp)):
    os.makedirs(download_temp)
if not (os.path.isdir(torrent_dir)):
    os.makedirs(torrent_dir)

downloadTorrentFiles()
uploadTorrents()
if delete_stopped_and_complete:
    cleanUpTorrents()