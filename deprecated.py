import warnings
warnings.warn('use of this module is deprecated', DeprecationWarning)

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
		self.dependency_names = self.get_dependency_names(self.dependencies,
														  dependencies_dir)
	
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

# def _get_nested_args():
# 	args = []
# 	for arg in sys.argv:
# 		if arg in {'-i', '--pip-install-in-virtualenv'}:
# 			args.append('--pip-install-here')
# 		else:
# 			args.append(arg)


# def install_dependencies(dependencies_dir, requirements_txt):
# 	pip_main(['install', '-r', requirements_txt,
# 			  '--find-links', 'file://' + os.path.abspath(dependencies_dir)])
#
#
# def install_here(dependencies_dir, pip_args):
# 	pip_main(['install', '--find-links', 'file://' + os.path.abspath(dependencies_dir)] + args)


# def build_venv(args):
# 	virtualenv = VirtualEnv(args.destination, args.virtualenv_zip)
# 	virtualenv.ensure_existence()
# 	exit_code = rerun_in_virtualenv(virtualenv)
# 	sys.exit(exit_code)


# def validate_and_set_defaults(args):
# 	if args.destination is None:
# 		args.destination = 'deployment'
# 	if args.dependencies is None:
# 		if os.path.isdir('dependencies'):
# 			args.dependencies = 'dependencies'
# 		else:
# 			print 'No dependencies folder specified, and "./dependencies" does'\
# 				  ' not exist, so skipping local dependency installation.'
# 	elif not os.path.isdir(args.dependencies):
# 		raise OSError('Dependencies folder not found: {}'.format(args.dependencies))


# def rerun_in_virtualenv(virtualenv):
# 	rerun_flag = '--__INTERNAL_FLAG_DONT_USE__running-in-virtualenv'
# 	return virtualenv.run_in_virtualenv([__file__] + sys.argv[1:] + [rerun_flag])
#
# def install_in_virtualenv(virtualenv, vd_args, pip_args):
# 	return virtualenv.run_in_virtualenv(
# 		[__file__] + vd_args + ['--pip-install-here'] + pip_args
# 	)
