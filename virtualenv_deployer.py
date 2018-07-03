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

YES = False


class SystemStrings:
	BIN_DIR = {'Linux': 'bin', 'Windows': 'Scripts'}[platform.system()]
	EXE = {'Windows': '.exe'}.get(platform.system(), '')
	BAT = {'Windows': '.bat'}.get(platform.system(), '')
	SH = {'Linux': 'sh'}.get(platform.system(), '')
	RETURN = {'Windows': '\r\n'}.get(platform.system(), '\n')


def main(clargs=None):
	if clargs is None:
		clargs = sys.argv[1:]
	args = _parse_args(clargs)
	virtualenv = VirtualEnv(args.destination, args.virtualenv_zip)
	if args.install_here:
		installer = Installer(args.dependencies)
		if args.requirements is not None:
			installer.install_requirements(args.requirements)
		if args.pip_install is not None:
			installer.install(args.pip_install)
	else:
		virtualenv.ensure_existence()
		virtualenv.run_inside([__file__] + ['--install-here'] + clargs)


def get_virtualenv(clargs=None):
	if clargs is None:
		clargs = sys.argv[1:]
	args = _parse_args(clargs)
	return VirtualEnv(args.destination, args.virtualenv_zip)


def _parse_args(clargs=None):
	parser = argparse.ArgumentParser()
	parser.add_argument('-y', '--yes', action='store_true')
	parser.add_argument('-o', '--destination')
	parser.add_argument('-d', '--dependencies')
	parser.add_argument('-r', '--requirements')
	parser.add_argument('-v', '--virtualenv-zip')
	parser.add_argument('-i', '--pip-install', nargs=argparse.REMAINDER,
						help='Run pip install <args> in the virtualenv. Only '
							 'use this option as the final option, because '
							 'everything following it will be assumed to be '
							 'pip arguments.')
	parser.add_argument('--install-here', action='store_true',
						help='Use this flag to indicate the script is being '
							 'called from within the virtualenv, and it should '
							 'install distributions directly into the calling '
							 'python installation.')
	args = parser.parse_args(clargs)
	_resolve_arguments(args)
	if args.yes:
		global YES
		YES = True
	return args


def _resolve_arguments(args):
	"""Don't just use default values because default values are treated special"""
	if args.destination is None:
		cwd = os.getcwd()
		print('Deploying to working directory: ' + cwd)
		args.destination = cwd
	args.dependencies = _resolve_item(args.dependencies, 'dependencies',
									  os.path.isdir, 'local dependencies')
	args.requirements = _resolve_item(args.requirements, 'requirements.txt',
									  os.path.isfile, 'requirements file')
	args.virtualenv_zip = _resolve_item(args.virtualenv_zip, 'virtualenv.zip',
										os.path.isfile, 'pre-existing virtualenv.zip')


def _resolve_item(specified, default, checker, name=''):
	if specified is not None:
		if checker(specified):
			return specified
		else:
			raise ValueError('Not found: "{}"'.format(specified))
	else:
		if checker(default):
			print('Using default {}: "{}"'.format(name, default))
			return default
		else:
			print('"{}" not found. Not using {}'.format(default, name))


class Installer(object):
	_pip_main = None
	
	def __init__(self, local_packages=None):
		self.common_pip_args = []
		if local_packages is not None:
			self.common_pip_args += ['--find-links',
									 'file://' + os.path.abspath(local_packages)]
	
	def install_requirements(self, requirements_txt):
		self.install(['-r', requirements_txt])
	
	def install(self, pip_args):
		self.pip_main(['install'] + self.common_pip_args + pip_args)
	
	@property
	def pip_main(self):
		if self._pip_main is None:
			try:
				from pip import main as pip_main
			except ImportError:
				from pip._internal import main as pip_main
			self._pip_main = pip_main
		return self._pip_main


class VirtualEnv(object):
	VERSION = '16.0.0'
	
	def __init__(self, destination, virtualenv_zip=None):
		self.home = os.path.join(destination, 'virtualenv')
		self.zip = virtualenv_zip
		self.bin_dir = os.path.join(self.home, platform.system(), SystemStrings.BIN_DIR)
		self.python = os.path.join(self.bin_dir, 'python' + SystemStrings.EXE)
		self.activate = os.path.join(self.bin_dir, 'activate' + SystemStrings.BAT)
		self._activate_this = os.path.join(self.bin_dir, 'activate_this.py')
		self.tmp = os.path.join(self.home, 'tmp')
		self.os_folder = os.path.join(self.home, platform.system())
		
	def ensure_existence(self):
		if not self.integrity_check():
			msg = 'A virtual environment is required, and you do not appear to' \
				  ' have one.\nWould you like to install a virtual environment?'
			if yn(msg, 'y'):
				self.setup()
			else:
				raise RuntimeError('Valid virtual environment not installed.')
	
	def integrity_check(self):
		try:
			print('Validating python executable exists with correct major version...')
			validate_command([self.python, '-c',
							  'import sys; print("python " + str(sys.version_info[0]))'],
							 "python " + str(sys.version_info[0]) + '\n')
			print('Validating activate exists and executes without error...')
			validate_command(([SystemStrings.SH] if SystemStrings.SH else []) + [self.activate])
		except (OSError, RuntimeError) as e:
			print('virtualenv is not valid: ' + str(e))
			return False
		print('virtualenv appears to be valid.')
		return True
	
	def setup(self):
		if self.zip is None:
			makedirs_delete_existing(self.tmp)
			print('Downloading virtualenv...')
			self.zip = self.download_source()
		print('Extracting virtualenv...')
		extract_zip(self.zip, self.tmp)
		print('virtualenv source acquired.')
		virtualenvpy = os.path.join(self.tmp, 'virtualenv-{}'.format(self.VERSION),
									'virtualenv.py')
		makedirs_delete_existing(self.os_folder)
		self.create(virtualenvpy)
	
	def download_source(self):
		local = os.path.join(self.tmp, 'venv_{}.zip'.format(self.VERSION))
		url = 'https://github.com/pypa/virtualenv/archive/{}.zip'.format(self.VERSION)
		urlretrieve(url, local)
		return local
	
	def create(self, virtualenvpy):
		virtualenv = imp.load_source('virtualenv', virtualenvpy)
		orig_sys_argv = sys.argv
		sys.argv = ['virtualenv.py', self.os_folder]
		virtualenv.main()
		sys.argv = orig_sys_argv
	
	def run_inside(self, args):
		process = subprocess.Popen([self.python] + args)
		process.communicate()
		return process.returncode
	
	def install_inside(self, pip_args):
		return self.run_inside(['-m', 'pip', 'install', pip_args])
	
	def activate_this(self):
		execfile(self._activate_this, dict(__file__=self._activate_this))


def validate_command(args, expected_stdout=b'', expected_stderr=b'',
					 expected_returncode=0):
	process = subprocess.Popen(args, stdout=subprocess.PIPE,
							   stderr=subprocess.PIPE)
	stdout, stderr = [i.decode("utf-8") for i in process.communicate()]
	if process.returncode != expected_returncode:
		raise RuntimeError('{} exited with incorrect return code: '
						   'expected {}, actual {}\n\nstdout:\n{}\n\nstderr:\n{}\n\n'
						   .format(args, expected_returncode, process.returncode, stdout, stderr))
	stdout, stderr, expected_stdout, expected_stderr = \
		neutralize(stdout), neutralize(stderr), \
		neutralize(expected_stdout), neutralize(expected_stderr)
	if stdout != expected_stdout:
		raise RuntimeError('{} output incorrect stdout:\nexpected: '
						   '{}\nactual: {}'.format(args, repr(expected_stdout), repr(stdout)))
	if stderr != expected_stderr:
		raise RuntimeError('{} output incorrect stderr:\nexpected: '
						   '{}\nactual: {}'.format(args, repr(expected_stderr), repr(stderr)))


def neutralize(s):
	return str(s).replace('\r', '')


def makedirs_delete_existing(path):
	if os.path.isdir(path):
		if yn('{} already exists, delete and re-create?'.format(path), 'y'):
			shutil.rmtree(path)
		else:
			raise RuntimeError('Failed to delete {}'.format(path))
	os.makedirs(path)


def extract_zip(source, destination):
	zip_ref = zipfile.ZipFile(source, 'r')
	zip_ref.extractall(destination)
	zip_ref.close()


def yn(prompt, preference=None):
	if YES:
		return True
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


if __name__ == '__main__':
	main()
