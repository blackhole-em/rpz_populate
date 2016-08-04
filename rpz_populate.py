#!/opt/soltra/edge/bin/python2.7
import sys, pymongo, getopt, datetime, shutil, difflib
zonefile = "/var/named/ctc.response-policy"
sinkhole = "1.1.1.1"
mywlist = "/root/whitelist"
pname = "ctc.response-policy"
def getSerial(zfile):
	with open(zfile, 'r') as zf:
		for l in zf:
			if "; serial" in l:
				s = int(l.split()[0])
				s += 1
				return s
def getWhitelist():
	with open(mywlist, 'r') as wf:
		wlist = wf.read().splitlines()
	return wlist
def getSoltraDomains(wlist):
	domainlist = []
	query = {'data.api.object.properties.xsi:type':{'$in':['AddressObjectType','LinkObjectType','URIObjectType','DomainNameObjectType']}}
	MONGODB_URI = 'mongodb://127.0.0.1:27017/inbox'
	client = pymongo.MongoClient(MONGODB_URI)
	db = client.get_default_database()
	soltra = db['stix']
	results = soltra.find(query,{'data.api.object.properties':1})
	for result in results:
		if result["data"]["api"]["object"]["properties"]["xsi:type"] == 'DomainNameObjectType':
			mydmn = result["data"]["api"]["object"]["properties"]["value"]
			if type(mydmn) is dict:
				for myd in mydmn["value"]:
					if myd not in domainlist:
						domainlist.append(myd)
			else:
				if mydmn not in domainlist and mydmn not in wlist:
					domainlist.append(mydmn)
	return domainlist
def backupConfig(infile):
	now = datetime.datetime.now().strftime("%Y%m%d_%H%M%s")
	bfile = "/usr/local/backup/"+pname+"."+now
	shutil.copy(infile, bfile)
	print "****  Backup file located at: "+bfile+" ****"
	return bfile
def buildHeader(zfile,snum):
	dmn_header = '''$TTL    600
@                       1D IN SOA       localhost root (
                                        '''+str(snum)+'''              ; serial
                                        3H              ; refresh
                                        15M             ; retry
                                        1W              ; expiry
                                        1D )            ; minimum

@ IN NS localhost.'''
	with open(zfile, 'w') as myf:
		myf.write(dmn_header+"\n")
def buildZone(zfile,domainlist):
	with open(zfile, 'a') as myf:
		for dmn in domainlist:
			myf.write(dmn.strip()+" A "+sinkhole+"\n")
def findStr(s,file):
	with open(file, "r") as inl:
		for l in inl:
			if s in l:
				return True
	return False
def configDiff(zfile,slist):
	myl = []
	for dmn in slist:
		if not findStr(dmn.strip(),zfile):
			print "New Domain Added To Sinkhole - "+dmn
			myl.append(dmn)
	if not myl:
		print "No New domains to sinkhole"
		return False
	else:
		return True
			
def main():
	try:
		print "**** Backing up configs ****"
		bfile = backupConfig(zonefile)
		print "**** Getting whitelist domains ****"
		wlist = getWhitelist()
		print "**** Getting latest serial number ****"
		snum = getSerial(zonefile)
		print "**** Getting Soltra Domains ****"
		slist = getSoltraDomains(wlist)
		print "**** Building Zonefile Header ****"
		buildHeader(zonefile,snum)
		print "**** Building Zonefile ****"
		buildZone(zonefile,slist)
		print "**** RPZ Updated Successful ****"
		if configDiff(bfile,slist):
			print "**** To update Infoblox, now run: ****"
			print "****            rndc reload        ****"
	except Exception as e:
		print "======== Error: "+str(e)
		print "==== RPZ Update Failed ===="

if __name__ == "__main__":
    main()
