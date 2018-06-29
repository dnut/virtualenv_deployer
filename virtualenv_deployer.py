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

_pip_main = None


def pip_main(*args, **kwargs):
	global _pip_main
	if _pip_main is None:
		try:
			from pip import main as pip_main
		except ImportError:
			from pip._internal import main as pip_main
		_pip_main = pip_main
	return _pip_main(*args, **kwargs)


class SystemStrings:
	BIN_DIR = {'Linux': 'bin', 'Windows': 'Scripts'}[platform.system()]
	EXE = {'Windows': '.exe'}.get(platform.system(), '')
	BAT = {'Windows': '.bat'}.get(platform.system(), '')
	SH = {'Linux': 'sh'}.get(platform.system(), '')
	RETURN = {'Windows': '\r\n'}.get(platform.system(), '\n')


def main():
	args = parse_args()
	if not args.__INTERNAL_FLAG_DONT_USE__running_in_virtualenv:
		virtualenv = VirtualEnv(args.destination, args.virtualenv_zip)
		virtualenv.ensure_existence()
		exit_code = rerun_in_virtualenv(virtualenv)
		sys.exit(exit_code)
	else:
		# dependency_handler = DependencyHandler(args.dependencies, args.requirements)
		# dependency_handler.install_unmet()
		install_dependencies(args.dependencies, args.requirements)


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-y', '--yes', action='store_true')
	parser.add_argument('-o', '--destination')
	parser.add_argument('-d', '--dependencies')
	parser.add_argument('-r', '--requirements')
	parser.add_argument('-v', '--virtualenv-zip')
	parser.add_argument('--__INTERNAL_FLAG_DONT_USE__running-in-virtualenv',
						action='store_true')
	args = parser.parse_args()
	resolve_arguments(args)
	return args


def resolve_arguments(args):
	if args.destination is None:
		cwd = os.getcwd()
		print 'Deploying to working directory: ' + cwd
		args.destination = cwd
	args.dependencies = resolve_item(args.dependencies, 'dependencies',
									 os.path.isdir, 'local dependencies')
	args.requirements = resolve_item(args.requirements, 'requirements.txt',
									 os.path.isfile, 'requirements file')
	args.virtualenv_zip = resolve_item(args.virtualenv_zip, 'virtualenv.zip',
									   os.path.isfile, 'pre-existing virtualenv.zip')


def resolve_item(specified, default, checker, name=''):
	if specified is not None:
		if checker(specified):
			return specified
		else:
			raise ValueError('Not found: "{}"'.format(specified))
	else:
		if checker(default):
			print 'Using default {}: "{}"'.format(name, default)
			return default
		else:
			print '"{}" not found. Not using {}'.format(default, name)


def validate_and_set_defaults(args):
	if args.destination is None:
		args.destination = 'deployment'
	if args.dependencies is None:
		if os.path.isdir('dependencies'):
			args.dependencies = 'dependencies'
		else:
			print 'No dependencies folder specified, and "./dependencies" does'\
				  ' not exist, so skipping local dependency installation.'
	elif not os.path.isdir(args.dependencies):
		raise OSError('Dependencies folder not found: {}'.format(args.dependencies))


def rerun_in_virtualenv(virtualenv):
	rerun_flag = '--__INTERNAL_FLAG_DONT_USE__running-in-virtualenv'
	return virtualenv.run_in_virtualenv([__file__] + sys.argv[1:] + [rerun_flag])


class VirtualEnv(object):
	VERSION = '16.0.0'
	
	def __init__(self, destination, virtualenv_zip=None):
		self.home = os.path.join(destination, 'virtualenv')
		self.zip = virtualenv_zip
		self.bin_dir = os.path.join(self.home, platform.system(), SystemStrings.BIN_DIR)
		self.python = os.path.join(self.bin_dir, 'python' + SystemStrings.EXE)
		self.activate = os.path.join(self.bin_dir, 'activate' + SystemStrings.BAT)
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
	
	def run_in_virtualenv(self, args):
		process = subprocess.Popen([self.python] + args)
		process.communicate()
		return process.returncode


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
	return str(s.replace('\r', ''))


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


def install_dependencies(dependencies_dir, requirements_txt):
	pip_main(['install', '-r', requirements_txt,
			  '--find-links', 'file://' + os.path.abspath(dependencies_dir)])


class DependencyHandler(object):
	"""The entire job of this class can be accomplished with the
	install_dependencies function, however that function always imports pip,
	which takes a long time, and is a problem if we want to run this script
	right before every time we run an application, so this is an attempt to
	replicate some basic pip functionality to check dependencies before actually
	importing pip. It definitely needs some work before it can be considered
	reliable, eg:
	TODO: Check for dist info folder to see if package is installed?
	"""
	def __init__(self, dependencies_dir, requirements_txt):
		self.requirements = self.convert_requirements_to_list(requirements_txt)
		self.dependencies = self.convert_dependencies_to_list(dependencies_dir)
		self.dependency_names = self.get_dependency_names(self.dependencies, dependencies_dir)
	
	@staticmethod
	def get_dependency_names(dependencies, dependencies_dir):
		names_txt = os.path.join(dependencies_dir, 'names.txt')
		if os.path.isfile(names_txt):
			with open(names_txt) as f:
				names = [i.strip() for i in f.readlines() if i]
			return names
		return [os.path.split(d)[1].partition('-')[0] for d in dependencies]
	
	@staticmethod
	def convert_requirements_to_list(requirements_txt):
		if not os.path.isfile(requirements_txt) or requirements_txt is None:
			print('No requirements file at {}'.format(requirements_txt))
			return []
		with open(requirements_txt) as f:
			return [pkg.rstrip('\n').replace('-', '_') for pkg in f.readlines()]
	
	@classmethod
	def convert_dependencies_to_list(cls, dependencies_dir):
		if not os.path.isdir(dependencies_dir) or dependencies_dir is None:
			print('No dependencies directory at {}'.format(dependencies_dir))
			return []
		generic = cls._convert_dependecies_to_list(dependencies_dir)
		os_dependencies_dir = os.path.join(dependencies_dir, platform.system())
		os_specific = []
		if os.path.isdir(os_dependencies_dir):
			os_specific = cls._convert_dependecies_to_list(os_dependencies_dir)
		return generic + os_specific
	
	@staticmethod
	def _convert_dependecies_to_list(dependencies_dir):
		return [os.path.join(dependencies_dir, filename)
				for filename in os.listdir(dependencies_dir)
				if filename[-2:] in ('hl', 'gz', 'gg')]
	
	def get_unmet(self):
		unmet = []
		for dependency in self.dependency_names:
			try:
				imp.find_module(dependency)
			except ImportError:
				print(dependency, 'not found')
				unmet = self.dependencies
				break
		for requirement in self.requirements:
			try:
				imp.find_module(requirement)
			except ImportError:
				unmet.append(requirement)
		return unmet
	
	def install_unmet(self):
		install_these = self.get_unmet()
		if len(install_these) > 0:
			try:
				from pip import main as pip_main
			except ImportError:
				from pip._internal import main as pip_main
			print('Installing dependencies: {}'.format(install_these))
			for pkg in install_these:
				pip_main(['install', pkg])


if __name__ == '__main__':
	main()
