__version__ = "0.0.14"

import os
import sys
from bluepy.btle import Scanner, DefaultDelegate
import pandas as pd

import psutil
import logging

def restart_program():
    """Restarts the current program, with file objects and descriptors
       cleanup
    """

    try:
        p = psutil.Process(os.getpid())
        for handler in p.get_open_files() + p.connections():
            os.close(handler.fd)
    except Exception, e:
        logging.error(e)

    python = sys.executable
    os.execl(python, python, *sys.argv)
	
def update(dl_url, force_update=False):
    """
Attempts to download the update url in order to find if an update is needed.
If an update is needed, the current script is backed up and the update is
saved in its place.
"""
    import urllib
    import re
    from subprocess import call
    def compare_versions(vA, vB):
        """
Compares two version number strings
@param vA: first version string to compare
@param vB: second version string to compare
@author <a href="http_stream://sebthom.de/136-comparing-version-numbers-in-jython-pytho/">Sebastian Thomschke</a>
@return negative if vA < vB, zero if vA == vB, positive if vA > vB.
"""
        if vA == vB: return 0

        def num(s):
            if s.isdigit(): return int(s)
            return s

        seqA = map(num, re.findall('\d+|\w+', vA.replace('-SNAPSHOT', '')))
        seqB = map(num, re.findall('\d+|\w+', vB.replace('-SNAPSHOT', '')))

        # this is to ensure that 1.0 == 1.0.0 in cmp(..)
        lenA, lenB = len(seqA), len(seqB)
        for i in range(lenA, lenB): seqA += (0,)
        for i in range(lenB, lenA): seqB += (0,)

        rc = cmp(seqA, seqB)

        if rc == 0:
            if vA.endswith('-SNAPSHOT'): return -1
            if vB.endswith('-SNAPSHOT'): return 1
        return rc

    # dl the first 256 bytes and parse it for version number
    try:
        http_stream = urllib.urlopen(dl_url)
        update_file = http_stream.read(256)
        http_stream.close()
    except IOError, (errno, strerror):
        print "Unable to retrieve version data"
        print "Error %s: %s" % (errno, strerror)
        return 0

    match_regex = re.search(r'__version__ *= *"(\S+)"', update_file)
    if not match_regex:
        print "No version info could be found"
        return 0
    update_version = match_regex.group(1)
	
    print(update_version)
	
    if not update_version:
        print "Unable to parse version data"
        return 0

    if force_update:
        print "Forcing update, downloading version %s..." \
            % update_version
    else:
        cmp_result = compare_versions(__version__, update_version)
        if cmp_result < 0:
            print "Newer version %s available, downloading..." % update_version
        elif cmp_result > 0:
            print "Local version %s newer then available %s, not updating." \
                % (__version__, update_version)
            return 0
        else:
            print "You already have the latest version."
            return 0

	
    import sys
    # dl, backup, and save the updated script
    app_path = os.path.realpath(sys.argv[0])

    if not os.access(app_path, os.W_OK):
        print "Cannot update -- unable to write to %s" % app_path

    dl_path = app_path + ".new"
    backup_path = app_path + ".old"
    try:
        dl_file = open(dl_path, 'w')
        http_stream = urllib.urlopen(dl_url)
        total_size = None
        bytes_so_far = 0
        chunk_size = 8192
        try:
            total_size = int(http_stream.info().getheader('Content-Length').strip())
        except:
            # The header is improper or missing Content-Length, just download
            dl_file.write(http_stream.read())

        while total_size:
            chunk = http_stream.read(chunk_size)
            dl_file.write(chunk)
            bytes_so_far += len(chunk)

            if not chunk:
                break

            percent = float(bytes_so_far) / total_size
            percent = round(percent*100, 2)
            sys.stdout.write("Downloaded %d of %d bytes (%0.2f%%)\r" %
                (bytes_so_far, total_size, percent))

            if bytes_so_far >= total_size:
                sys.stdout.write('\n')

        http_stream.close()
        dl_file.close()
    except IOError, (errno, strerror):
        print "Download failed"
        print "Error %s: %s" % (errno, strerror)
        return 0

    try:
        os.rename(app_path, backup_path)
    except OSError, (errno, strerror):
        print "Unable to rename %s to %s: (%d) %s" \
            % (app_path, backup_path, errno, strerror)
        return 0

    try:
        os.rename(dl_path, app_path)
    except OSError, (errno, strerror):
        print "Unable to rename %s to %s: (%d) %s" \
            % (dl_path, app_path, errno, strerror)
        return 0

    try:
        import shutil
        shutil.copymode(backup_path, app_path)
    except:
        os.chmod(app_path, 0755)

    print "New version installed as %s" % app_path
    print "(previous version backed up to %s)" % (backup_path)
    return 1


class ScanDelegate(DefaultDelegate):
	def __init__(self):
		DefaultDelegate.__init__(self)

	def handleDiscovery(self, dev, isNewDev, isNewData):
		if isNewDev:
			print("Discovered device", dev.addr)
		elif isNewData:
			print("Received new data from", dev.addr)

if __name__ == '__main__':
	while(True):
		status = update('https://raw.githubusercontent.com/arash-ash/FaceLink/master/beacon_scan.py')
		if status == 1:
			restart_program()
		scanner = Scanner().withDelegate(ScanDelegate())
		devices = scanner.scan(2.0)

		dict = {}
	#	try :
		for dev in devices:
			dict[dev.addr] = dev.rssi
	#		print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
		for (adtype, desc, value) in dev.getScanData():
			print("  %s = %s" % (desc, value))

		file = open('data.html', 'w+')
		df = pd.DataFrame.from_dict(dict, orient='index')
		df = df.sort_values(0)
		data = df.to_html()
		file.write(data)
		file.close()
	#	except:
	#		print('no device found!')
