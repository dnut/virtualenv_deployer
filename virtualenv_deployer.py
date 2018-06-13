import argparse
import imp
import os
import platform
import shutil
import subprocess
import sys
import zipfile
# Python 2/3 compatibility
try:
	from urllib import urlretrieve
except ImportError:
	from urllib.request import urlretrieve
try:
	input = raw_input
except NameError:
	pass

VIRTUALENV_VERSION = '16.0.0'


class SystemStrings:
	BIN_DIR = {'Linux': 'bin', 'Windows': 'Scripts'}[platform.system()]
	EXE = {'Windows': '.exe'}.get(platform.system(), '')
	BAT = {'Windows': '.bat'}.get(platform.system(), '')
	SH = {'Linux': ['sh']}.get(platform.system(), [])


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-y', '--yes', action='store_true')
	parser.add_argument('-o', '--destination')
	parser.add_argument('-d', '--dependencies')
	parser.add_argument('-r', '--requirements')
	parser.add_argument('--__INTERNAL_FLAG_DONT_USE__running-in-virtualenv',
						action='store_true')
	return parser.parse_args()


def check_for_venv(path):
	bin_dir = os.path.join(path, platform.system(), SystemStrings.BIN_DIR)
	python = os.path.join(bin_dir, 'python' + SystemStrings.EXE)
	activate = os.path.join(bin_dir, 'activate' + SystemStrings.BAT)
	try:
		validate_command([python, '-c', 'import sys; print("python " + str(sys.version_info[0]))'],
						 ("python " + str(sys.version_info[0])) + '\n')
		validate_command(SystemStrings.SH + [activate])
	except (OSError, RuntimeError) as e:
		print('virtualenv is not valid: ' + str(e))
		return False
	return True


def validate_command(args, expected_stdout=b'', expected_stderr=b'', expected_returncode=0):
	process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = [i.decode("utf-8") for i in process.communicate()]
	if process.returncode != expected_returncode:
		raise RuntimeError('{} exited with incorrect return code: '
						   'expected {}, actual {}\n\nstdout:\n{}\n\nstderr:\n{}\n\n'
						   .format(args, expected_returncode, process.returncode,
								   stdout, stderr))
	if stdout != expected_stdout:
		raise RuntimeError('{} output incorrect stdout:\nexpected: '
						   '{}\nactual: {}'.format(args, expected_stdout, stdout))
	if stderr != expected_stderr:
		raise RuntimeError('{} output incorrect stderr:\nexpected: '
						   '{}\nactual: {}'.format(args, expected_stderr, stderr))


def activate_virtualenv(path):
	bin_dir = {'Linux': 'bin', 'Windows': 'Scripts'}[platform.system()]
	activate_this = os.path.join(path, platform.system(), bin_dir, 'activate_this.py')
	execfile(activate_this, dict(__file__=activate_this))
	
	
def makedirs_overwrite(path):
	if os.path.isdir(path):
		shutil.rmtree(path)
	os.makedirs(path)


def download_virtualenv(destination, version):
	url = 'https://github.com/pypa/virtualenv/archive/{}.zip'.format(version)
	local = os.path.join(destination, 'venv_{}.zip'.format(version))
	print('Downloading virtualenv...')
	urlretrieve(url, local)
	zip_ref = zipfile.ZipFile(local, 'r')
	print('Extracting virtualenv...')
	zip_ref.extractall(destination)
	zip_ref.close()
	print('virtualenv source acquired.')


def create_virtualenv(source, destination):
	virtualenv = imp.load_source('virtualenv', source)
	orig_sys_argv = sys.argv
	sys.argv = ['virtualenv.py', destination]
	virtualenv.main()
	sys.argv = orig_sys_argv


def setup_virtualenv(root):
	tmp = os.path.join(root, 'tmp')
	os_venv = os.path.join(root, platform.system())
	makedirs_overwrite(tmp)
	download_virtualenv(tmp, VIRTUALENV_VERSION)
	virtualenvpy = os.path.join(tmp, 'virtualenv-{}'.format(VIRTUALENV_VERSION), 'virtualenv.py')
	makedirs_overwrite(os_venv)
	create_virtualenv(virtualenvpy, os_venv)


def yn(prompt, preference=None):
	if preference is None:
		yn_prompt = 'y, n'
	else:
		yn_prompt = {'y': 'Y, n', 'n': 'y, N'}[preference.lower()]
	while True:
		yn = input(prompt + '\n:: [{}] '.format(yn_prompt))
		yes = yn.lower() == 'y' or yn.lower() == 'yes'
		no = yn.lower() == 'n' or yn.lower() == 'no'
		if yes or no:
			return yes
		elif preference is None:
			print('You must select either y or n.')
		else:
			return preference.lower() == 'y'


def requirements_list(requirements_file):
	if requirements_file is None:
		return []
	with open(requirements_file) as f:
		return [pkg.rstrip('\n').replace('-', '_') for pkg in f.readlines()]


def dependencies_list(dependencies_dir):
	if dependencies_dir is None:
		return []
	return [os.path.join(dependencies_dir, filename) for filename
			in os.listdir(dependencies_dir) if filename[-2:] in ('hl', 'gz', 'gg')]


def rerun_in_virtualenv(python):
	args = [python, __file__] + sys.argv[1:]\
		   + ['--__INTERNAL_FLAG_DONT_USE__running-in-virtualenv']
	process = subprocess.Popen(args)
	process.communicate()
	return process.returncode


if __name__ == '__main__':
	args = parse_args()
	if not args.__INTERNAL_FLAG_DONT_USE__running_in_virtualenv:
		WORKING_DIR = os.path.join(args.destination, 'venv')
		if not check_for_venv(WORKING_DIR):
			msg = 'A virtual environment is required, and you do not appear to'\
				  ' have one.\nWould you like to install a virtual environment?'
			if yn(msg, 'y'):
				setup_virtualenv(WORKING_DIR)
			else:
				raise RuntimeError('Valid virtual environment not installed.')
		python = os.path.join(WORKING_DIR, platform.system(), SystemStrings.BIN_DIR,
							  'python' + SystemStrings.EXE)
		sys.exit(rerun_in_virtualenv(python))
	else:
		try:
			from pip import main as pip_main
		except ImportError:
			from pip._internal import main as pip_main
		for pkg in dependencies_list(args.dependencies)\
				+ requirements_list(args.requirements):
			pip_main(['install', pkg])
