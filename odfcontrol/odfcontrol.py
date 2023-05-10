# odfcontrol.py
#
# Written by: Ryan Tanner
# email: ryan.tanner@nasa.gov
# 
# This file is part of ESA's XMM-Newton Scientific Analysis System (SAS).
#
#    SAS is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    SAS is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with SAS.  If not, see <http://www.gnu.org/licenses/>.

# odfcontrol.py

"""
odfcontrol.py

"""

# Standard library imports
import os, sys, subprocess, shutil, glob, tarfile, gzip

# Third party imports
# (se below for astroquery)

# Local application imports
# from .version import VERSION, SAS_RELEASE, SAS_AKA
# from pysas.wrapper import Wrapper as wrap
from pysas.logger import TaskLogger as TL


# __version__ = f'odfcontrol (startsas-{VERSION}) [{SAS_RELEASE}-{SAS_AKA}]' 
__version__ = 'odfcontrol (odfcontrol-0.1)'

logger = TL('odfcontrol')

class ODF:
    """
    Class for observation data files (ODF).

        An odfid and data_dir are necessary.

        data_dir is the base directory where you store all XMM data.

        Data is organized as:
            data_dir = /path/to/data/
            odf_data_dir = /path/to/data/odfid/
        With subdirectories and files:
                odf_dir  = /path/to/data/odfid/ODF/
                work_dir = /path/to/data/odfid/work/
                SAS_CCF  = work_dir/ccf.cif
                SAS_ODF  = work_dir/*SUM.SAS

    """

    def __init__(self,odfid,data_dir):
        self.odfid = odfid
        self.data_dir = data_dir

    def inisas(self,sas_dir,sas_ccfpath,verbosity = 4,suppress_warning = 1):
        """
        Simple wrapper for inisas defined below.
        """

        self.sas_dir = sas_dir
        self.sas_ccfpath = sas_ccfpath
        self.verbosity = verbosity
        self.suppress_warning = suppress_warning

        inisas(sas_dir, sas_ccfpath, verbosity = verbosity, suppress_warning = suppress_warning)

    def setodf(self,odfid=None,data_dir=None,level='ODF',sasfiles=False,
               sas_ccf=None,sas_odf=None,cifbuild_opts=None,odfingest_opts=None,
               encryption_key=None,overwrite=False,repo='esa'):
        """
        Inputs:

            --odfid:          (string): ID of ODF in string format.

            --data_dir:  (string/path): Path to directory where the data will be 
                                        downloaded. Automatically creates directory
                                        <workdir>/<odfid>.
                                        Default: 'pwd', returns the current directory.

            --sasfiles:      (boolean): If True: Data is assumed to be in <workdir>/<odfid>.
                                        Both sas_ccf and sas_odf must be defined.

            --sas_ccf:   (string/path): Path to .ccf file for odfid.

            --sas_odf:   (string/path): Path to SUM.SAS file for odfid.

            --level:          (string): Level of data products to download.
                                        Default: 'ODF'
                                        Can be 'ODF, 'PPS' or 'ALL'.

            --cifbuild_opts:  (string): Options for cifbuild.

            --odfingest_opts: (string): Options for odfingest.

            --encryption_key: (string): Encryption key for propietary data, a string 32 
                                        characters long. -OR- path to file containing 
                                        ONLY the encryption key.

            --overwrite:     (boolean): If True will force overwrite of data if odfid 
                                        data already exists in <workdir>/.

            --repo:           (string): Which repository to use to download data. 
                                        Default: 'esa'
                                        Can be either
                                        'esa' (data from Europe/ESA) or 
                                        'heasarc' (data from North America/NASA) or
                                        'sciserver' (if user is on sciserver)

        Either an odfid must be given or sasfiles must be set to True.

        The task produces a log file named 'startsas.log' which is found in 
        the directory from where the task is started. 
        The log file always collect the maximum of debugging information.
        However, the level of information shown in the console is modulated
        via the verbosity option  '-V/--verbosity.
        """

        self.odfid = odfid
        self.data_dir = data_dir
        self.level = level
        self.sas_ccf = sas_ccf
        self.sas_odf = sas_odf
        self.cifbuild_opts = cifbuild_opts
        self.odfingest_opts = odfingest_opts
        self.encryption_key = encryption_key
        self.repo = repo

        # Check if inputs are compatable.

        if not odfid and not sasfiles:
            logger.log('error', 'Either an odfid must be given -OR- sasfiles = True') 
            raise Exception('Either an odfid must be given -OR- sasfiles = True')
        
        if odfid:
            if sas_ccf or sas_odf:
                logger.log('error', 'Parameter odfid given and sas_ccf and sas_odf are set. \nEither use an odfid or set sas_ccf and sas_odf. Not both.')
                raise Exception('Parameter odfid icompatible with sas_ccf and sas_odf')

        if sasfiles:
            if not sas_ccf and not sas_odf:
                logger.log('error', 'Parameters sas_ccf and sas_odf must be set if sasfiles = True') 
                raise Exception('Parameters sas_ccf and sas_odf must be set if sasfiles = True')


        #logger.log('warning', f'Executing {__file__} {iparsdic}')

        # Checking LHEASOFT, SAS_DIR and SAS_CCFPATH

        lheasoft = os.environ.get('LHEASOFT')
        if not lheasoft:
            logger.log('error', 'LHEASOFT is not set. Please initialise HEASOFT')
            raise Exception('LHEASOFT is not set. Please initialise HEASOFT')
        else:
            logger.log('info', f'LHEASOFT = {lheasoft}')

        sasdir = os.environ.get('SAS_DIR')
        if not sasdir:
            logger.log('error', 'SAS_DIR is not defined. Please initialise SAS')
            raise Exception('SAS_DIR is not defined. Please initialise SAS')
        else:
            logger.log('info', f'SAS_DIR = {sasdir}') 

        sasccfpath = os.environ.get('SAS_CCFPATH')
        if not sasccfpath:
            logger.log('error', 'SAS_CCFPATH not set. Please define it')
            raise Exception('SAS_CCFPATH not set. Please define it')
        else:
            logger.log('info',f'SAS_CCFPATH = {sasccfpath}')

        # Where are we?
        startdir = os.getcwd()
        logger.log('info',f'startsas was initiated from {startdir}')

        if self.data_dir == None:
            self.data_dir = startdir
            
        # If data_dir was not given as an absolute path, it is interpreted
        # as a subdirectory of startdir
        if self.data_dir[0] != '/':
            self.data_dir = os.path.join(startdir, self.data_dir)
        elif self.data_dir[:2] == './':
            self.data_dir = os.path.join(startdir, self.data_dir[2:])
        
        logger.log('info', f'Data directory = {self.data_dir}')

        if not os.path.isdir(self.data_dir):
            logger.log('warning', f'{self.data_dir} does not exist. Creating it!')
            os.mkdir(self.data_dir)
            logger.log('info', f'{self.data_dir} has been created!')
        
        os.chdir(self.data_dir)
        logger.log('info', f'Changed directory to {self.data_dir}')

        print(f'''

        Starting SAS session

        Data directory = {self.data_dir}

        ''')

        # Identify the download level
        levelopts = ['ODF', 'PPS', 'ALL']
        if level not in levelopts:
            logger.log('error', 'ODF request level is undefined!')
            print(f'Options for level are {levelopts[0]}, {levelopts[1]}, or {levelopts[2]}')
            raise Exception('ODF request level is undefined!')
        else:
            logger.log('info', f'Will download ODF with level {level}') 

        # Set directories for the observation, odf, and working
        obs_dir = os.path.join(self.data_dir,odfid)
        odf_dir = os.path.join(obs_dir,'ODF')
        pps_dir = os.path.join(obs_dir,'PPS')
        working_dir = os.path.join(obs_dir,'working')

        # Processing odfid
        if odfid:
            # Checks if obs_dir exists. Removes it if overwrite = True.
            # Default overwrite = False.
            if os.path.exists(obs_dir):
                if overwrite:
                    logger.log('info', f'Removing existing directory {obs_dir} ...')
                    print(f'\n\nRemoving existing directory {obs_dir} ...')
                    shutil.rmtree(obs_dir)
                else:
                    logger.log('error', f'Existing directory for {odfid} found ...')
                    print(f'Directory for {odfid} found, will not overwrite.')
                    print('Force overwrite with: overwrite = True')
                    raise Exception(f'Directory for {odfid} found, will not overwrite.')
            
            # Creates subdirectory odfid to move or unpack observation files
            # and makes subdirectories.
            logger.log('info', f'Creating observation directory {obs_dir} ...')
            print(f'\nCreating observation directory {obs_dir} ...')
            os.mkdir(obs_dir)
            logger.log('info', f'Creating working directory {working_dir} ...')
            print(f'Creating working directory {working_dir} ...')
            if not os.path.exists(working_dir): os.mkdir(working_dir)

            logger.log('info', 'Requesting odfid = {} from XMM-Newton Science Archive\n'.format(odfid))
            print('Requesting odfid = {} from XMM-Newton Science Archive\n'.format(odfid))
                
            if repo == 'esa':
                logger.log('info', f'Changed directory to {obs_dir}')
                os.chdir(obs_dir)
                odftar = odfid + '.tar.gz'
                # Removes tar file if already present.
                if os.path.exists(odftar):
                    os.remove(odftar)
                if level == 'ALL':
                    level = ['ODF','PPS']
                else:
                    level = [level]
                for levl in level:
                    # Download the odfid from ESA, using astroquery
                    from astroquery.esa.xmm_newton import XMMNewton
                    logger.log('info', f'Downloading {odfid}, level {levl} into {obs_dir}')
                    print(f'\nDownloading {odfid}, level {levl} into {obs_dir}. Please wait ...\n')
                    XMMNewton.download_data(odfid, level=levl)
                    # Check that the tar.gz file has been downloaded
                    try:
                        os.path.exists(odftar)
                        logger.log('info', f'{odftar} found.') 
                    except FileExistsError:
                        logger.log('error', f'File {odftar} is not present. Not downloaded?')
                        print(f'File {odftar} is not present. Not downloaded?')
                        sys.exit(1)

                    if levl == 'ODF':    
                        os.mkdir(odf_dir)
                    elif levl == 'PPS':
                        os.mkdir(pps_dir)

                    # Untars the odfid.tar.gz file
                    logger.log('info', f'Unpacking {odftar} ...')
                    print(f'\nUnpacking {odftar} ...\n')

                    try:
                        with tarfile.open(odftar,"r:gz") as tar:
                            if levl == 'ODF':
                                tar.extractall(path=odf_dir)
                            elif levl == 'PPS':
                                tar.extractall(path=pps_dir)
                        os.remove(odftar)
                        logger.log('info', f'{odftar} extracted successfully!')
                        logger.log('info', f'{odftar} removed')
                    except tarfile.ExtractError:
                        logger.log('error', 'tar file extraction failed')
                        raise Exception('tar file extraction failed')
            elif repo == 'heasarc':
                #Download the odfid from HEASARC, using wget
                if level == 'ALL':
                    levl = ''
                else:
                    levl = level
                logger.log('info', f'Downloading {odfid}, level {levl}')
                print(f'\nDownloading {odfid}, level {level}. Please wait ...\n')
                cmd = f'wget -m -nH -e robots=off --cut-dirs=4 -l 2 -np https://heasarc.gsfc.nasa.gov/FTP/xmm/data/rev0/{odfid}/{levl}'
                result = subprocess.run(cmd, shell=True)
                for path, directories, files in os.walk('.'):
                    for file in files:
                        if 'index.html' in file:
                            os.remove(os.path.join(path,file))
                    for direc in directories:
                        if '4XMM' in direc:
                            shutil.rmtree(os.path.join(path,direc))
                        if level == 'ODF' and direc == 'PPS':
                            shutil.rmtree(os.path.join(path,direc))
                        if level == 'PPS' and direc == 'ODF':
                            shutil.rmtree(os.path.join(path,direc))
            elif repo == 'sciserver':
                # Copies data into personal storage space.
                dest_dir = obs_dir
                if level == 'ALL':
                    levl = ''
                else:
                    levl = level
                    dest_dir = os.path.join(dest_dir,levl)
                if levl == 'ODF':    
                    os.mkdir(odf_dir)
                elif levl == 'PPS':
                    os.mkdir(pps_dir)
                archive_data = f'/home/idies/workspace/headata/FTP/xmm/data/rev0//{odfid}/{levl}'
                logger.log('info', f'Copying data from {archive_data} ...')
                print(f'\nCopying data from {archive_data} ...')
                shutil.copytree(archive_data,dest_dir,dirs_exist_ok=True)

            # Check if data is encrypted. Decrypt the data.
            encrypted = glob.glob('**/*.gpg', recursive=True)
            if len(encrypted) > 0:
                logger.log('info', f'Encrypted files found! Decrypting files!')

                # Checks for encryption key or file with key.
                # If no encryption key is given then go looking for a file.
                encryption_file = None
                if encryption_key == None:
                    encryption_file = glob.glob(os.path.join(self.data_dir,f'*{odfid}*'))
                    if len(encryption_file) == 0:
                        encryption_file = glob.glob(os.path.join(self.data_dir,'*key*'))
                    if len(encryption_file) > 1:
                        logger.log('error', 'Multiple possible encryption key files. Specify encryption key file.')
                        raise Exception('Multiple possible encryption key files.')
                    if len(encryption_file) == 0:
                        encryption_file = 'None'
                    if os.path.isfile(encryption_file[0]):
                        logger.log('info', f'File with encryption key found: {encryption_file}')
                    else:
                        print('File decryption failed. No encryption key found.')
                        print(f'Regular file with the encryption key needs to be placed in: {self.data_dir}')
                        logger.log('error', 'File decryption failed. No encryption key found.')
                        raise Exception('File decryption failed. No encryption file found.')
                elif os.path.isfile(encryption_key):
                    logger.log('info', f'Ecryption key is in file: {encryption_key}')
                    encryption_file = encryption_key
                if encryption_file is not None:
                    logger.log('info', f'Reading ecryption key from: {encryption_file}')
                    with open(encryption_file) as f:
                        lines = f.readlines()
                        encryption_key = lines[0]
                if encryption_key == None:
                    print(f'No encryption key found in {encryption_file}')
                    print(f'Regular file with the encryption key needs to be placed in: {self.data_dir}')
                    logger.log('error', 'File decryption failed. No encryption key found.')
                    raise Exception('File decryption failed. No encryption key found.')
                
                    
                for file in encrypted:
                    out_file = file[:-4]
                    if os.path.exists(out_file):
                        logger.log('info', f'Already decrypted file found: {out_file}')
                        print(f'Already decrypted file found: {out_file}')
                    else:
                        logger.log('info', f'Decrypting {file}')
                        cmd = 'echo {0} | gpg --batch -o {1} --passphrase-fd 0 -d {2}'.format(encryption_key,out_file,file)
                        result = subprocess.run(cmd, shell=True)
                        if result.returncode != 0:
                            print(f'Problem decrypting {file}')
                            logger.log('error', f'File decryption failed, key used {encryption_key}')
                            raise Exception('File decryption failed')
                        os.remove(file)
                        logger.log('info', f'{file} removed')
            else:
                logger.log('info','No encrypted files found.')

            for file in glob.glob('**/*.gz', recursive=True):
                logger.log('info', f'Unpacking {file} ...')
                print(f'Unpacking {file} ...')
                with gzip.open(f'{file}', 'rb') as f_in:
                    out_file = file[:-3]
                    with open(out_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(file)
                logger.log('info', f'{file} removed')

            for file in glob.glob('**/*.TAR', recursive=True):
                logger.log('info', f'Unpacking {file} ...')
                print(f'Unpacking {file} ...')
                with tarfile.open(file,"r") as tar:
                    tar.extractall(path=odf_dir)
                os.remove(file)
                logger.log('info', f'{file} removed')
            
            if level == 'PPS':
                ppsdir = os.path.join(self.data_dir, odfid, 'pps')
                ppssumhtml = 'P' + odfid + 'OBX000SUMMAR0000.HTM'
                ppssumhtmlfull = os.path.join(ppsdir, ppssumhtml)
                ppssumhtmllink = 'file://' + ppssumhtmlfull
                logger.log('info', f'PPS products can be found in {ppsdir}')
                print(f'\nPPS products can be found in {ppsdir}\n\nLink to Observation Summary html: {ppssumhtmllink}')
            else:
                os.chdir(odf_dir)
                logger.log('info', f'Changed directory to {odf_dir}')

                # Checks that the MANIFEST file is there
                MANIFEST = glob.glob('MANIFEST*')
                try:
                    os.path.exists(MANIFEST[0])
                    logger.log('info', f'File {MANIFEST[0]} exists')
                except FileExistsError:
                    logger.log('error', f'File {MANIFEST[0]} not present. Please check ODF!')
                    print(f'File {MANIFEST[0]} not present. Please check ODF!')
                    sys.exit(1)

                # Here the ODF is fully untarred below odfid subdirectory
                # Now we start preparing the SAS_ODF and SAS_CCF
                logger.log('info', f'Setting SAS_ODF = {odf_dir}')
                print(f'\nSetting SAS_ODF = {odf_dir}')
                os.environ['SAS_ODF'] = odf_dir

                # Change to working directory
                os.chdir(working_dir)
                # Run cifbuild
                if cifbuild_opts:
                    cifbuild_opts_list = cifbuild_opts.split(" ") 
                    cmd = ['cifbuild']
                    cmd = cmd + cifbuild_opts_list
                    logger.log('info', f'Running cifbuild with {cifbuild_opts} ...')
                    print(f'\nRunning cifbuild with {cifbuild_opts} ...')
                else:
                    cmd = ['cifbuild']
                    logger.log('info', f'Running cifbuild...')
                    print(f'\nRunning cifbuild...')
                
                rc = subprocess.run(cmd)
                if rc.returncode != 0:
                    logger.log('error', 'cifbuild failed to complete')
                    raise Exception('cifbuild failed to complete')
                
                # Check whether ccf.cif is produced or not
                ccfcif = glob.glob('ccf.cif')
                try:
                    os.path.exists(ccfcif[0])
                    logger.log('info', f'CIF file {ccfcif[0]} created')
                except FileExistsError:
                    logger.log('error','The ccf.cif was not produced')
                    print('ccf.cif file is not produced')
                    sys.exit(1)
                
                # Sets SAS_CCF variable
                fullccfcif = os.path.join(working_dir, 'ccf.cif')
                logger.log('info', f'Setting SAS_CCF = {fullccfcif}')
                print(f'\nSetting SAS_CCF = {fullccfcif}')
                os.environ['SAS_CCF'] = fullccfcif

                # Now run odfingest
                if odfingest_opts:
                    odfingest_opts_list = odfingest_opts.split(" ")
                    cmd = ['odfingest'] 
                    cmd = cmd + odfingest_opts_list
                    logger.log('info', f'Running odfingest with {odfingest_opts} ...')
                    print(f'\nRunning odfingest with {odfingest_opts} ...')
                else:
                    cmd = ['odfingest']
                    logger.log('info','Running odfingest...') 
                    print('\nRunning odfingest...')
                
                rc = subprocess.run(cmd)
                if rc.returncode != 0:
                    logger.log('error', 'odfingest failed to complete')
                    raise Exception('odfingest failed to complete.')
                else:
                    logger.log('info', 'odfingest successfully completed')

                # Check whether the SUM.SAS has been produced or not
                sumsas = glob.glob('*SUM.SAS')
                try:
                    os.path.exists(sumsas[0])
                    logger.log('info', f'SAS summary file {sumsas[0]} created')
                except FileExistsError:
                    logger.log('error','SUM.SAS file was not produced') 
                    print('SUM.SAS file was not produced')
                    sys.exit(1)
                
                # Set the SAS_ODF to the SUM.SAS file
                fullsumsas = os.path.join(working_dir, sumsas[0])
                os.environ['SAS_ODF'] = fullsumsas
                logger.log('info', f'Setting SAS_ODF = {fullsumsas}')
                print(f'\nSetting SAS_ODF = {fullsumsas}')
                
                # Check that the SUM.SAS file has the right PATH keyword
                with open(fullsumsas) as inf:
                    lines = inf.readlines()
                for line in lines:
                    if 'PATH' in line:
                        key, path = line.split()
                        if path != odf_dir:
                            logger.log('error', f'SAS summary file PATH {path} mismatchs {odf_dir}')
                            raise Exception(f'SAS summary file PATH {path} mismatchs {odf_dir}')
                        else:
                            logger.log('info', f'Summary file PATH keyword matches {odf_dir}')
                            print(f'\nWarning: Summary file PATH keyword matches {odf_dir}')

                print(f'''\n\n
                SAS_CCF = {fullccfcif}
                SAS_ODF = {fullsumsas}
                \n''')

        elif sasfiles:
            
            sasccf = sas_ccf
            sasodf = sas_odf 

            if sasccf[0] != '/':
                raise Exception(f'{sasccf} must be defined with absolute path')

            if sasodf[0] != '/':
                raise Exception(f'{sasodf} must be defined with absolute path')

            try:
                os.path.exists(sasccf)
                logger.log('info', f'{sasccf} is present')
            except FileExistsError:
                logger.log('error', f'File {sasccf} not found.')
                print(f'File {sasccf} not found.')
                sys.exit(1)

            try:
                os.path.exists(sasodf)
                logger.log('info', f'{sasodf} is present')
            except FileExistsError:
                logger.log('error', f'File {sasodf} not found.')
                print(f'File {sasodf} not found.')
                sys.exit(1)
            
            os.environ['SAS_CCF'] = sasccf
            logger.log('info', f'SAS_CCF = {sasccf}')
            print(f'SAS_CCF = {sasccf}')

            if 'SUM.SAS' not in sas_odf:
                logger.log('error', '{} does not refer to a SAS SUM file'.format(sas_odf))
                raise Exception('{} does not refer to a SAS SUM file'.format(sas_odf))
            
            # Check that the SUM.SAS file PATH keyword points to a real ODF directory
            with open(sasodf) as inf:
                lines = inf.readlines()
            for line in lines:
                if 'PATH' in line:
                    key, path = line.split()
                    if not os.path.exists(path):
                        logger.log('error', f'Summary file PATH {path} does not exist.')
                        raise Exception(f'Summary file PATH {path} does not exist.')
                    MANIFEST = glob.glob(os.path.join(path, 'MANIFEST*'))
                    if not os.path.exists(MANIFEST[0]):
                        logger.log('error', f'Missing {MANIFEST[0]} file in {path}. Missing ODF components?')
                        raise Exception(f'\nMissing {MANIFEST[0]} file in {path}. Missing ODF components?')
            
            os.environ['SAS_ODF'] = sasodf
            logger.log('info', f'SAS_ODF = {sasodf}')
            print(f'SAS_ODF = {sasodf}')




def inisas(sas_dir, sas_ccfpath, verbosity = 4, suppress_warning = 1):
    """
    Heasoft must be initialized first, separately.

    Inputs are:

        - sas_dir (required) directory where SAS is installed.

        - sas_ccfpath (required) directory where calibration files are located.

        - verbosity (optional, default = 4) SAS verbosity.

        - suppress_warning (optional, default = 1) 
    """
    
    def add_environ_variable(variable,invalue,prepend=True):
        """
        variable (str) is the name of the environment variable to be set.
        
        value (str, or list) is the value to which the environment variable
        will be set.
        
        prepend (boolean) default=True, whether to prepend or append the 
        variable
        
        The function first checks if the enviroment variable already exists.
        If not it will be created and set to value.
        If veriable alread exists the function will check if value is already
        present. If not it will add it either prepending (default) or appending.

        Returns
        -------
        None.

        """
        
        if isinstance(invalue, str):
            listvalue = [invalue]
        else:
            listvalue = invalue
            
        if not isinstance(listvalue, list):
            raise Exception('Input to add_environ_variable must be str or list!')
        
        for value in listvalue:
            environ_var = os.environ.get(variable)
            
            if not environ_var:
                os.environ[variable] = value
            else:
                splitpath = environ_var.split(os.pathsep)
                if not value in splitpath:
                    if prepend:
                        splitpath.insert(0,value)
                    else:
                        splitpath.append(value)
                os.environ[variable] = os.pathsep.join(splitpath)

    # Checking LHEASOFT and inputs

    lheasoft = os.environ.get('LHEASOFT')
    if not lheasoft:
        raise Exception('LHEASOFT is not set. Please initialise HEASOFT')
    if sas_dir is None:
        raise Exception('sas_dir must be provided to initialize SAS using initializesas.')
    if sas_ccfpath is None:
        raise Exception('sas_ccfpath must be provided to initialize SAS using initializesas.')

    add_environ_variable('SAS_DIR',sas_dir)
    add_environ_variable('SAS_CCFPATH',sas_ccfpath)
    add_environ_variable('SAS_PATH',[sas_dir])
    
    binpath = [os.path.join(sas_dir,'bin'), os.path.join(sas_dir,'bin','devel')]
    libpath = [os.path.join(sas_dir,'lib'),os.path.join(sas_dir,'libextra'),os.path.join(sas_dir,'libsys')]
    perlpath = [os.path.join(sas_dir,'lib','perl5')]
    pythonpath = [os.path.join(sas_dir,'lib','python')]

    add_environ_variable('SAS_PATH',binpath+libpath+perlpath+pythonpath,prepend=False)
    add_environ_variable('PATH',binpath)
    add_environ_variable('LIBRARY_PATH',libpath,prepend=False)
    add_environ_variable('LD_LIBRARY_PATH',libpath,prepend=False)
    add_environ_variable('PERL5LIB',perlpath)
    add_environ_variable('PYTHONPATH',pythonpath)

    perllib = os.environ.get('PERLLIB')
    if perllib:
        splitpath = perllib.split(os.pathsep)
        add_environ_variable('PERL5LIB',splitpath,prepend=False)

    os.environ['SAS_VERBOSITY'] = '{}'.format(verbosity)
    os.environ['SAS_SUPPRESS_WARNING'] = '{}'.format(suppress_warning)

def download_data(odfid,data_dir,level='ODF',encryption_key=None,overwrite=False,repo='esa'):
    """
    Downloads, or copies, data from chosen repository.
    """