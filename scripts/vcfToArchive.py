#!/usr/bin/env python

from optparse import OptionParser  
import gzip, yaml, re, sys, os, shutil

# based on vcfToMageTab.py

def get_read_fileHandler(aFilename):
    '''
    ' Open aFilename for reading and return
    ' the file handler.  The file can be
    ' gzipped or not.
    '''
    if aFilename.endswith('.gz'):
        return gzip.open(aFilename,'rb')
    else:
        return open(aFilename,'r')


def get_write_fileHandler(aFilename):
    '''
    ' Open aFilename for writing and return
    ' the file handler.  The file can be
    ' gzipped or not.
    '''
    if aFilename.endswith('.gz'):
        return gzip.open(aFilename,'wb')
    else:
        return open(aFilename,'w')

class idfParams(object):
    """Parse input yaml file to IDF parameter object"""
    def __init__(self, inputYaml):
        with open(inputYaml) as handle:
            self.params = yaml.load(handle.read())
        handle.close()

        # do we have all inputs?
        expected = ['expDesign', 'expDesignOntology', 'expDesignFactorName', 'expDesignFactorType', 'investigationTitle',
          'personLastName', 'personFirstName', 'personMidInitial', 'personEmail', 'personAddress', 
          'personAffiliation', 'personRole', 'pubMedId', 'pubAuthors', 'pubTitle', 'pubStatus', 
          'expDescription', 'protocolNames', 'protocolTypes', 'protocolDescriptions', 
          'protocolOntologies', 'protocolParameters', 'ontologyName', 'ontologyFile', 
          'ontologyVersion']
        found = set(self.params.keys())
        if set(expected).difference(found):
            for mis in set(expected).difference(found):
                sys.stderr.write("ERROR, missing %s in yaml inputs\n" % mis)
            sys.exit(1)

        if set(found).difference(expected):
            for toomuch in set(found).difference(expected):
                sys.stderr.write("WARNING, %s in yaml inputs does not match to an input variable, ignoring...\n" % toomuch)
        self.name = os.path.basename(inputYaml)[:-4]	# remove yml extension

def sanity_check(idfObjects):
    if len(idfObjects) < 1:
        print >>sys.stderr, "ERROR, no yaml format input files found in yamlDir, exiting..."
        sys.exit(1)
    names = set()
    for obj in idfObjects:
        if obj.params["protocolNames"] in names:
            print >>sys.stderr, "ERROR: duplicate name %s in yaml input, please correct" % obj.params["protocolNames"]
            sys.exit(1)
        names.add(obj.params["protocolNames"])

def getProtocolRef(idfObjects, softwareName):
    """Returns protocol reference and center ID for use in SDRF"""
    for obj in idfObjects:
        if obj.name == softwareName:
            return obj.params["protocolNames"], obj.params["protocolNames"].split(":")[0]
    return False

def getGenome(line):
            if ("GRCh37-lite" in line):
                genome = "GRCh37-lite"
            elif ("GRCh37" in line):
                genome = "GRCh37"
            elif ("Homo_sapiens_assembly19" in line):
                genome = "hg19"
            elif ("hg19" in line):
                genome = "hg19"
            elif ("hg18" in line):
                genome = "hg18"
            elif ("NCBI36" in line):
                genome = "36.1"
            elif ("NCBI37" in line):
                genome = "37"
            else:
                genome = None
            return genome

class SDRF(object):
    def __init__(self, fromSample):
        if fromSample:
            self.sampleSDRF(fromSample)
        else:
            self.uuid = "Extract Name"
    	    self.barcode = "Comment [TCGA Barcode]"
            self.isTumor = "Comment [is tumor]"
            self.material = "Material Type"
    	    self.annot = "Annotation REF"
    	    self.genome = "Comment [TCGA Genome Reference]"
            self.protocol1 = "Protocol REF"
            self.vendor =  "Parameter Value [Vendor]"
            self.catalogName = "Parameter Value [Catalog Name]"
            self.catalogNr = "Parameter Value [Catalog Number]"
            self.protocol2 = "Protocol REF"
            self.bamfile = "Comment [Derived Data File REF]"
            self.cghubId = "Comment [TCGA CGHub ID]"
            self.include1 = "Comment [TCGA Include for Analysis]"
            self.protocol3 = "Protocol REF"
            self.vcf = "Derived Data File"
            self.tcgaSpec = "Comment [TCGA Spec Version]"
            self.include2 =  "Comment [TCGA Include for Analysis]"
            self.datatype = "Comment [TCGA Data Type]"
            self.dataLevel = "Comment [TCGA Data Level]"
            self.archive = "Comment [TCGA Archive Name]"

##SAMPLE=<ID=NORMAL,Description="Normal sample",SampleUUID=6a71666e-fc7c-4bd8-ae31-31c3322b03e9,SampleTCGABarcode=TCGA-00-0000-10A-00A-0000-00,AnalysisUUID=1fa3a6c6-68a1-4e8f-a72f-a5d4a76a3758,File="testexome.pair0.normal.bam",Platform="Illumina",Source="dbGAP",Accession="dbGaP",softwareName=<pindel>,softwareVer=<0.2.5b1>,softwareParam=<>>
##SAMPLE=<ID=PRIMARY,Description="Primary Tumor",SampleUUID=15d1322f-c272-42fa-abe5-d0f0e9cabba5,SampleTCGABarcode=TCGA-00-0000-01A-00A-0000-00,AnalysisUUID=1d20ac06-389b-4105-a74b-f69b72886639,File="testexome.pair0.tumour.bam",Platform="Illumina",Source="dbGAP",Accession="dbGaP",softwareName=<pindel>,softwareVer=<0.2.5b1>,softwareParam=<>>
    def sampleSDRF(self, line):
        sampleLine = line[len("##SAMPLE=<"):len(line)-1]	# remove outer <>
        params = dict(item.split("=") for item in sampleLine.split(","))
        # remove the quotes
        for key in params:
            if (params[key].startswith("\"")):
                value = params[key]
                params[key] = value[1:(len(value)-1)]
        self.uuid = params['SampleUUID']
        self.barcode = params['SampleTCGABarcode']
        self.isTumor = None
        if params['ID'] == 'NORMAL':
            self.isTumor = 'no'
        elif params['ID'] == 'PRIMARY':
            self.isTumor = 'yes'
        self.material = 'DNA'		# NOTE: hardcoded, must parse from header when adding RNA data
	self.annot = '->'
	self.genome = None	# TBD
        self.protocol1 = '->'
        self.vendor = '->'
        self.catalogName = '->'
        self.catalogNr = '->'
        self.protocol2 = '->'
        self.bamfile = params['File']	
        self.cghubId = params['Source']	# dbGaP
        self.include1 = "yes"
        self.protocol3 = None	# TBD, this is the protocol as listed in the IDF
        self.vcf = None		# TBD
        self.tcgaSpec = None	# TBD
        self.include2 =  "yes"
        self.datatype = "Mutations"
        self.dataLevel = "Level 2"
        self.archive = None	# TBD
        self.software = params['softwareName']	# does not go in SDRF, will need this later
        self.individual = ('-').join(params['SampleTCGABarcode'].split('-')[0:3])

    def addVcfInfo(self, genome, tcgaSpec, archive):
        self.genome = genome
        self.tcgaSpec = tcgaSpec
        self.archive = archive

    def addExternal(self, protocolRef, vcf):
        self.vcf = vcf
        self.protocol3 = protocolRef

    def doPrint(self):
        printList = [self.uuid, self.barcode, self.isTumor, self.material, self.annot, 
            self.genome, self.protocol1, self.vendor, self.catalogName, self.catalogNr, 
            self.protocol2, self.bamfile, self.cghubId, self.include1, self.protocol3, 
            self.vcf, self.tcgaSpec, self.include2, self.datatype, self.dataLevel, 
            self.archive]
        if None in printList:
            print >>sys.stderr, "SDRF output contains illegal None value:\n", printList
            sys.exit(1)
        return "\t".join(printList)

def sdrfFromVcf(vcfFile, archive):
    """Create SDRF objects from VCF input"""

    sdrfList = []
    tcgaSpecVersion = None
    genome = None
    
    # open the file
    # we need to get (at least) two output samples from the VCF header: normal and primary tumor
    vcfFileHandler = get_read_fileHandler(vcfFile)
    for line in vcfFileHandler:
        # strip the carriage return and newline characters
        line = line.rstrip("\r\n")

        # if it is an empty line, then just continue
        if (line.isspace()):
            continue;
        # we need to extract the tcga spec that was used
        elif (line.startswith("##tcgaversion")):
            ##tcgaversion=1.0

            (key, value) = line.split("=")
            tcgaSpecVersion = value
        # we need to extract info from the reference tag in the header
        elif (line.startswith("##reference")):
            genome = getGenome(line)

        # Create one SDRF object for every SAMPLE found in the header
        elif (line.startswith("##SAMPLE")):
            mySDRF = SDRF(line)	# create SDRF object
            mySDRF.addVcfInfo(genome, tcgaSpecVersion, archive)
            sdrfList.append(mySDRF)

        elif (line.startswith("INFO") or line.startswith("FORMAT")):
            break

    vcfFileHandler.close()
    return sdrfList

def noneClean(v):
    if v is None:
        return ""
    return v

def concatIDF(idfObjectList, param):
    """Create tab separated strings from input yaml parameter objects"""
    outString = ""
    for obj in idfObjectList:
        outString += "\t" + str(noneClean(obj.params[param]))
    return outString

def createIDFfile(idfFilename, sdrfFilename, idfObjects):
    """Create IDF format output. This looks very similar to the expected yaml config input, but contains the sdrf filename and a title"""
    idfFileHandler = get_write_fileHandler(idfFilename)

    # output the experimental design lines
    idfFileHandler.write("".join(["Investigation Title", concatIDF(idfObjects, "investigationTitle")]) + "\n")
    idfFileHandler.write("".join(["Experimental Design", concatIDF(idfObjects, "expDesign")]) + "\n")
    idfFileHandler.write("".join(["Experimental Design Term Source REF", concatIDF(idfObjects, "expDesignOntology")]) + "\n")
    idfFileHandler.write("".join(["Experimental Factor Name", concatIDF(idfObjects, "expDesignFactorName")]) + "\n")
    idfFileHandler.write("".join(["Experimental Factor Type", concatIDF(idfObjects, "expDesignFactorType")]) + "\n")
    idfFileHandler.write("\n")

    # output the person lines
    idfFileHandler.write("".join(["Person Last Name", concatIDF(idfObjects, "personLastName")]) + "\n")
    idfFileHandler.write("".join(["Person First Name", concatIDF(idfObjects, "personFirstName")]) + "\n")
    idfFileHandler.write("".join(["Person Mid Initials", concatIDF(idfObjects, "personMidInitial")]) + "\n")
    idfFileHandler.write("".join(["Person Email", concatIDF(idfObjects, "personEmail")]) + "\n")
    idfFileHandler.write("".join(["Person Address", concatIDF(idfObjects, "personAddress")]) + "\n")
    idfFileHandler.write("".join(["Person Affiliation", concatIDF(idfObjects, "personAffiliation")]) + "\n")
    idfFileHandler.write("".join(["Person Roles", concatIDF(idfObjects, "personRole")]) + "\n")
    idfFileHandler.write("\n")

    # output the publication lines
    idfFileHandler.write("".join(["PubMed ID", concatIDF(idfObjects, "pubMedId")]) + "\n")
    idfFileHandler.write("".join(["Publication Author List", concatIDF(idfObjects, "pubAuthors")]) + "\n")
    idfFileHandler.write("".join(["Publication Title", concatIDF(idfObjects, "pubTitle")]) + "\n")
    idfFileHandler.write("".join(["Publication Status", concatIDF(idfObjects, "pubStatus")]) + "\n")
    idfFileHandler.write("".join(["Experiment Description", concatIDF(idfObjects, "expDescription")]) + "\n")
    idfFileHandler.write("\n")

# FIXME?
    # output the protocol lines
    idfFileHandler.write("".join(["Protocol Name", concatIDF(idfObjects, "protocolNames")]) + "\n")
    idfFileHandler.write("".join(["Protocol Type", concatIDF(idfObjects, "protocolTypes")]) + "\n")
    idfFileHandler.write("".join(["Protocol Description", concatIDF(idfObjects, "protocolDescriptions")]) + "\n")
    idfFileHandler.write("".join(["Protocol Term Source REF", concatIDF(idfObjects, "protocolOntologies")]) + "\n")
    idfFileHandler.write("".join(["Protocol Parameters", concatIDF(idfObjects, "protocolParameters")]) + "\n")
    idfFileHandler.write("\n")

    # output the sdrf line
    sdrfBasename = os.path.basename(sdrfFilename)
    idfFileHandler.write("\t".join(["SDRF Files", sdrfBasename]) + "\n")
    idfFileHandler.write("\n")

    # output the ontology lines
    idfFileHandler.write("".join(["Term Source Name", concatIDF(idfObjects, "ontologyName")]) + "\n")
    idfFileHandler.write("".join(["Term Source File", concatIDF(idfObjects, "ontologyFile")]) + "\n")
    idfFileHandler.write("".join(["Term Source Version", concatIDF(idfObjects, "ontologyVersion")]) + "\n")

    # close the file
    idfFileHandler.close()

def createSDRFfile(sdrfFile, sdrfObjects):
    """Create SDRF format output file from input list of SDRF objects"""

    sdrfFileHandler = get_write_fileHandler(sdrfFile)
    for sdrf in sdrfObjects:
        sdrfFileHandler.write(sdrf.doPrint() + "\n")
    sdrfFileHandler.close()


def createDir(mydir):
    if os.path.exists(mydir):
        print >>sys.stderr, "WARNING, overwriting", mydir
        shutil.rmtree(mydir)
    os.makedirs(mydir)


def main():

    # create the usage statement
    usage = """usage: python %prog <vcf dir> <idf.yaml dir> disease

From an input dir with VCF files, a dir with .yml format IDF input and a disease code (e.g. BRCA), 
create TCGA formatted Level_2 data and mage-tab archives.

NOTE: The correct IDF protocol for each input VCF is based on its name. This program expects inputs to be named
pindel.vcf, varscan.snp.vcf, etc. It may be better to parse this info from the VCF header.

"""
    cmdLineParser = OptionParser(usage=usage)
    if len(sys.argv) != 4:
        cmdLineParser.print_help()
        sys.exit(1)

    # get the required parameters
    (cmdLineOptions, cmdLineArgs) = cmdLineParser.parse_args()
    inputDir = str(cmdLineArgs[0])
    yamlDir = str(cmdLineArgs[1])
    disease = str(cmdLineArgs[2])
    archiveDir = disease

    # create output names
    # the outputdirs are of the format <domain>_<disease study>.Multicenter_mutation_calling_MC3.<archive type>.<serial index>.<revision>.<series>
    serial_index = "1"
    revision = "0"
    series = "0"
    version = (".").join([serial_index, revision, series])
    outBase = 'ucsc.edu_' + disease + '.Multicenter_mutation_calling_MC3'
    outMageTab = (".").join([outBase, "mage-tab", version]) 
    outData = (".").join([outBase, "Level_2", version]) 
    idfFilename = outBase + '.idf.txt'
    sdrfFilename = outBase + '.sdrf.txt'

    # overwrite output directories if need be
    createDir(archiveDir)
    mageTabDir = os.path.join(archiveDir, outMageTab)
    createDir(mageTabDir)
    dataDir = os.path.join(archiveDir, outData)
    createDir(dataDir)

    # parse the yaml format idf configs
    idfObjects = []
    for item in os.listdir(yamlDir):
        if item.endswith('yml'):
            idfObjects.append(idfParams(os.path.join(yamlDir, item)))
    sanity_check(idfObjects)

    # create the output IDF file
    createIDFfile(os.path.join(mageTabDir, idfFilename), sdrfFilename, idfObjects)

    # parse and copy VCF files while creating SDRF output
    sdrfOutput = []
    # header
    header = SDRF(fromSample=False)
    sdrfOutput.append(header)

    for vcfFile in os.listdir(inputDir):
        if vcfFile.endswith('vcf'):
            
            sdrfObjectList = sdrfFromVcf(os.path.join(inputDir, vcfFile), outData)
	    # copy and rename with center name and patient barcode
            # Note that there are two varscan outputs that have to be kept separate but point to the same IDF entry
            idfName = vcfFile.split(".")[0]	# radia, pindel...
            # find the correct protocol REF
            protocolRef, centerId = getProtocolRef(idfObjects, idfName)

            patient = sdrfObjectList[0].individual
            rename = ('.').join([vcfFile[:-4], centerId, sdrfObjectList[0].individual, 'vcf'])
            shutil.copyfile(os.path.join(inputDir, vcfFile), os.path.join(dataDir, rename))

	    # add info to SDRF objects
            for obj in sdrfObjectList:
                obj.addExternal(protocolRef, rename)

            # finally, add completed objects to output
            sdrfOutput.extend(sdrfObjectList)

    createSDRFfile(os.path.join(mageTabDir, sdrfFilename), sdrfOutput)

main()
sys.exit(0)