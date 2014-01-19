#!/usr/bin/env python
#
#
# hashsumcheck.py

import os
import hashlib
import sqlite3 as lite
import time
import sys
import argparse
import textwrap
from multiprocessing import (Process, Lock)

lock = Lock()

def writeDatabase(dirpathdata, hashfiledata, db_name):
        con = lite.connect(db_name)
        cur = con.cursor()
        
        lock.acquire()
        with con:
            ins = 'INSERT INTO hash_tbl(dirpath, hashfile) VALUES(\"' + dirpathdata + '\",\"' + hashfiledata + '\")'
            cur.execute(ins)
        lock.release()

def createHashFile(filepath):
        with open(filepath, 'rb') as f:
            m = hashlib.md5()
            data = f.read(8192)
            m.update(data)

            return m.hexdigest()

def listDirectory(directory, db_name):
        # check if directory defined
        # if not then exit
        if not os.path.isdir(directory):
            msg = "Directory not defined !!"
            parser = argparse.ArgumentParser()
            parser.error(msg)


        for dirname, dirnames, filenames in os.walk(directory):

            for filename in filenames:
                files = os.path.join(dirname, filename)

                p = Process(target=writeDatabase, args=(files.strip(), str(createHashFile(files.strip())), db_name))
                p.start()

                print filename + '\t\t\t\t' + createHashFile(files)

        print "Waiting for joining all process"                
        #p.join()

def checkHashFile(db_name):
        con = lite.connect(db_name)
        cur = con.cursor()
        marker = 0

        with con:
            r = cur.execute('SELECT dirpath FROM hash_tbl WHERE id=1')
            d = r.fetchone()
            directory = str(d[0])

        # check if directory exist
        if not os.path.isdir(directory):
            print "Directory doesn't exist !! \nExit.."
            sys.exit(1)

        print 'Checking file...\n'

        for dirname, dirnames, filenames in os.walk(directory):

            for filename in filenames:
                files = os.path.join(dirname, filename)
                hashsum = createHashFile(files.strip())

                with con:
                    res = cur.execute('SELECT hashfile FROM hash_tbl WHERE dirpath=\"' + files.strip() + '\"')
                    con.commit()
                    row = cur.fetchone()


                    with open('/var/log/hashsumcheck.log' , 'a') as f:
                        if row == None:
                            marker += 1
                            print '[-] New file created\t' + filename
                            print '\nCheck log in /var/log/hashsumcheck.log'
                            f.write('New file created at \t' + files + '\n')

                        elif row[0] == hashsum:
                            #if file matching with checksum then continue
                            continue
                            #print 'file matching'
                        else:
                            marker += 1
                            print '[x] File modification\t' + filename
                            print '\nCheck log in /var/log/hashsumcheck.log'
                            f.write('File modification at \t' + files + '\n')

        if marker == 0:
            print 'All file match..\nExit...'

def main():
        parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, 
                                            description=textwrap.dedent("""
                                                        This program purposed to generate hash for each files in your system
                                                        or your machine, for preventing file modification files or data and 
                                                        guarantee integration that files or data. If there's modification on
                                                        files or there's new file in your system, then the program will show warning 
                                                        message.And for path that files can you see in /var/log/hashsumcheck.log"""))

        parser.add_argument('--create-hash',  dest='create', action='store_true', help='list directory and create hash for all files')
        parser.add_argument('--check-hash',  dest='check', action='store_true', help='checking hash for all files')
        parser.add_argument('--dir', metavar="directory", dest='dir', type=str, help='directory name for hashing or checking files')
        parser.add_argument('--db', metavar="database-name", dest='dbase', type=str, required=True, help='database name for containing hash file')

        args = parser.parse_args()

        if args.create:
            con = lite.connect(str(args.dbase))
            cur = con.cursor()
            cur.execute("CREATE TABLE hash_tbl(id INTEGER PRIMARY KEY,dirpath TEXT, hashfile TEXT)")
            with con:
                cur.execute('INSERT INTO hash_tbl(dirpath) VALUES(\"'+ str(args.dir) +'\")')
            listDirectory(str(args.dir), str(args.dbase))
        elif args.check:
            if not os.path.isfile(str(args.dbase)):
                msg = "Database doesn't exist !!"
                parser = argparse.ArgumentParser()
                parser.error(msg)

            checkHashFile(str(args.dbase))
        else:
            parser.print_help()


if __name__ == '__main__':
        try:
            main()
        except Exception, e:
            raise e
            sys.exit(1)
