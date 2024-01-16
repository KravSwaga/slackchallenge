#/usr/env/bin python3.9
#slackconfig.py
#Author: Andrew Brennan


#import modules
import pexpect
import requests
import json
import getpass
import sys

#define functions
#import info from config.json
def import_json():
    try:
        with open('config.json','r+') as infile:
            data = json.load(infile)
            if data:
                return data
            else:
                return {}
    except IOError:
        print('Error: File config.json not found')
        return {}
    except json.decoder.JSONDecodeError as E:
        print('Error: Invalid config.json file')
        print(str(E))
        return {}
    #END IMPORT_JSON   

#Use pexpect to create ssh sessions on remote server        
def create_ssh_session(server):
    session = pexpect.spawn('ssh ' +username +'@' +server +' -o stricthostkeychecking=no')
    response = session.expect (['Permission denied', pexpect.TIMEOUT, "'s password: "], timeout=10)
    
    if response==2:
        #being asked for password
        session.sendline(password)
        try:
            pwvalid=session.expect('Welcome to Ubuntu', timeout=10)
            debuglog=str(session.before) + str(session.after)
            prompt=session.expect(':~# ', timeout=10)
            debuglog=debuglog + str(session.before) + str(session.after)
            #print(debuglog)
            print('Connected to '+server)
        except pexpect.exceptions.TIMEOUT:
            print('ERROR: timeout connecting to server' +server)
            debuglog=debuglog + str(session.before) + str(session.after)
            print(debuglog)
            sys.exit(1)
    
    return session
    #END CREATE_SSH_SESSION

def apt_install(session, instruction, attempt=0):
    name=instruction['name']
    command='apt install ' +name +' -y'
    verify=instruction['verify command']
    success=instruction['verify success']
    fail=instruction['verify fail']
    
    
    print('Checking ' +name +':')
    session.sendline(verify)
    check=session.expect([success,fail,pexpect.TIMEOUT])
    debuglog=''
    if check==2:
        print('ERROR: unable to check install due to timeout')
        return False
    elif check==1:
        print('Need to install ' +name)
        session.sendline(command)
        try:
            session.expect('The following NEW packages will be installed:',timeout=30)
            debuglog=str(session.before) + str(session.after)
            session.expect(':~# ', timeout=120)
            debuglog=debuglog + str(session.before) + str(session.after)
            #print(debuglog)
            print('Attempted install of ' +name)
            #lovely little bit of recursion with a counter to break it after 3 failed attempts
            if attempt<3:
                return apt_install(session, instruction, attempt+1)   
            else:
                print('Failed to install php after 3 attempts')
                return False
        except pexpect.exceptions.TIMEOUT:
            print(debuglog)
            return False        
    elif check==0:
        print(name +' is installed')
        return True
    #END CHECK_PHP

def create_file(content, name):
    print('Creating ' +name)
    outfile=open(name,'w+')
    outfile.write(content)
    outfile.close()
    #END CREATE_INDEXPHP

def upload_file(username, server, password, name, location):
    print('Copying ' +name +' to ' +location +' on ' +server)
    scpsession=pexpect.spawn('scp ' +name +' ' +username +'@' +server +':' +location +'/' +name)
    try:
        scpsession.expect("'s password",timeout=10)
        debuglog=str(scpsession.before) + str(scpsession.after)
        scpsession.sendline(password)
        scpsession.expect('100%',timeout=30)
        debuglog=debuglog + str(scpsession.before) + str(scpsession.after)
        session.expect(':~# ', timeout=10)
        debuglog=debuglog + str(scpsession.before) + str(scpsession.after)
        #print(debuglog)
    except pexpect.exceptions.TIMEOUT:
        print(debuglog)
        return False    

    return True
    #END COPY_INDEXPHP

def remove_oldfile(session, name, location):
    newfile=location +'/' +name
    print('Removing old ' +newfile)
    session.sendline('mv ' +newfile +' ' +newfile +'.old')
    status=session.expect(['No such file or directory',':~# ',pexpect.TIMEOUT], timeout=10)
    debuglog=str(session.before) + str(session.after)
    if status==0:
        print('INFO: ' +newfile +' does not exist, proceeding')
    elif status==1:
        print('INFO: ' +newfile +' renamed to ' +newfile +'.old, proceeding')
    elif status==2:
        print(debuglog)
        print('ERROR: failed to remove old ' +newfile +', check status manually')   
    #END REMOVE_INDEXHTML
 
def restart_service(server, service):
    print('Restarting ' +service)
    session.sendline('systemctl restart ' +service +'.service')
    try:
        session.expect(':~# ', timeout=10)
        debuglog=str(session.before) + str(session.after)
    except pexpect.exceptions.TIMEOUT:
        print(debuglog)
        return False
    
    return True
    #END RESTART_APACHE    
    

def check_curl(server):
    url='http://' +server
    print('Testing server response '+url)
    response=requests.get(url)
    if response.status_code==200:
        print(response.text)
        return response.text
    else:
        return False
    #END TEST_HELLOWORLD
 
#begin main
if __name__ == "__main__":

    #load parameters from config.json file
    print('*'*36)
    print('INFO: Loading configuration')
    config=import_json()
    
    print('*'*36)
    username=config['username']
    print('\nUsername: ' +username)

    print('*'*36)
    print('\nServer IPs:')
    for server in config['servers']:
        print(server)

    print('*'*36)
    print('\nInstruction set:')
    for instruction in config['instructions']:
        print(str(instruction) +'\n')    
   
    print('*'*36)
    password=getpass.getpass('Enter root password: ')

    for server in config['servers']:
        #create ssh session on server
        print('*'*36)
        print('Connecting to ' +server)
        session=create_ssh_session(server)
        
        for instruction in config['instructions']:
            if instruction['type']=="apt_install":
                print('*'*36)
                print("Executing apt_install of " +instruction['name'])
                apt_install(session, instruction)
            elif instruction['type']=="upload_file":
                print('*'*36)
                print('Uploading file to ' +server)
                create_file(instruction['content'], instruction['name'])
                remove_oldfile(session, instruction['name'], instruction['location'])
                upload_file(username, server, password, instruction['name'], instruction['location'])
            elif instruction['type']=="restart_service":
                print('*'*36)
                service=instruction['name']
                print('Restarting service ' + service)               
                restart_service(server, service)
            elif instruction['type']=="check_curl":
                response=check_curl(server)
                if response=='Hello, world!':
                    print('INFO: server ' +server + ' configured successfully!')
                else:
                    print('ERROR: Failed to configure server ' +server)
        
    print('*'*36)
    print('INFO: Completed')
    #END MAIN    

        

        
