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
            print(debuglog)
            sys.exit(1)
    
    return session
    #END CREATE_SSH_SESSION

#Check if php is installed and install it if required
def check_php(session, attempt=0):
    print('Checking PHP:')
    session.sendline('php -v')
    phpcheck=session.expect(['Zend Technologies',"Command 'php' not found",pexpect.TIMEOUT])
    if phpcheck==2:
        print('ERROR: unable to check for php due to timeout')
        return False
    elif phpcheck==1:
        print('Need to install php')
        session.sendline('apt install php7.2-cli -y')
        try:
            session.expect('The following additional packages will be installed',timeout=30)
            debuglog=str(session.before) + str(session.after)
            session.expect(':~# ', timeout=120)
            debuglog=debuglog + str(session.before) + str(session.after)
            #print(debuglog)
            print('Attempted install of PHP')
            #lovely little bit of recursion with a counter to break it after 3 failed attempts
            if attempt<3:
                return check_php(session,attempt+1)   
            else:
                print('Failed to install php after 3 attempts')
                return False
        except pexpect.exceptions.TIMEOUT:
            print(debuglog)
            return False        
    elif phpcheck==0:
        print('PHP is installed')
        return True
    #END CHECK_PHP

def check_apache(session,attempt=0):
    print('Checking Apache:')
    session.sendline('apache2 -v')
    phpcheck=session.expect(['Server version: Apache',"Command 'apache2' not found",pexpect.TIMEOUT])
    if phpcheck==2:
        print('ERROR: unable to check for Apache due to timeout')
        return False
    elif phpcheck==1:
        print('Need to install Apache')
        session.sendline('apt install libapache2-mod-php -y')
        try:
            session.expect('The following additional packages will be installed',timeout=30)
            debuglog=str(session.before) + str(session.after)
            session.expect(':~# ', timeout=120)
            debuglog=debuglog + str(session.before) + str(session.after)
            #print(debuglog)
            print('Attempted install of Apache')
            #lovely little bit of recursion with a counter to break it after 3 failed attempts
            if attempt<3:
                return check_apache(session,attempt+1)
            else:
                print('Failed to install Apache after 3 attempts')
                return False
        except pexpect.exceptions.TIMEOUT:
            print(debuglog)
            return False        
    elif phpcheck==0:
        print('Apache is installed')
        return True    
    #END CHECK_APACHE

def create_indexphp(php):
    print('Creating index.php')
    outfile=open('index.php','w+')
    outfile.write(php)
    outfile.close()
    #END CREATE_INDEXPHP

def copy_indexphp(username,server,password):
    print('Copying index.php to ' +server)
    scpsession=pexpect.spawn('scp index.php ' +username +'@' +server +':/var/www/html/index.php')
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

def remove_indexhtml(session):
    print('Removing old index.html')
    session.sendline('mv /var/www/html/index.html /var/www/html/index.html.old')
    status=session.expect(['No such file or directory',':~# ',pexpect.TIMEOUT], timeout=10)
    debuglog=str(session.before) + str(session.after)
    if status==0:
        print('INFO: index.html does not exist, proceeding')
    elif status==1:
        print('INFO: index.html renamed to index.html.old, proceeding')
    elif status==2:
        print(debuglog)
        print('ERROR: failed to remove index.html, check status manually in /var/www/html/ on ' +server)   
    #END REMOVE_INDEXHTML
 
def restart_apache(server):
    print('Restarting Apache')
    session.sendline('systemctl restart apache2.service')
    try:
        session.expect(':~# ', timeout=10)
        debuglog=str(session.before) + str(session.after)
    except pexpect.exceptions.TIMEOUT:
        print(debuglog)
        return False
    
    return True
    #END RESTART_APACHE    
    

def test_helloworld(server):
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
    php=config['php']
    print('\nUsername: ' +username)

    print('\nServer IPs:')
    for server in config['servers']:
        print(server)
    
    print('\nPHP application:')
    print(php)
    print('*'*36)
    
    password=getpass.getpass('Enter root password: ')

    #Create index.php file
    print('*'*36)
    create_indexphp(php)

    #server=config['servers'][0]
    for server in config['servers']:
        #create ssh session on server
        print('*'*36)
        print('Connecting to ' +server)
        session=create_ssh_session(server)
        
        #Check if php is installed, install it if not
        success=check_php(session)
        if not success:
            print('ERROR: failed to check/install PHP')
            sys.exit(1)
            
        #Check if Apache is installed, install it if notCheck if php is installed, install it if not
        success=check_apache(session)
        if not success:
            print('ERROR: failed to check/install Apache')
            sys.exit(1)

        #scp index.php file to server
        success=copy_indexphp(username,server,password)
        if not success:
            print('ERROR: failed to scp index.php to' +server)
            sys.exit(1)
        
        #remove_indexhtml(session)
        
        success=restart_apache(session)
        if not success:
            print('ERROR: failed to restart Apache on' +server)
            sys.exit(1)     

        response=test_helloworld(server)
        if response=='Hello, world!':
            print('INFO: server ' +server + ' configured successfully!')
        else:
            print('ERROR: Failed to configure server ' +server)
        
    print('*'*36)
    print('INFO: Completed')
    #END MAIN    

        

        
