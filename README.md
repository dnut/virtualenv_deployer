# virtualenv_deployer

Automatically deploy and maintain a virtualenv along with any combination of local and remote distributions. Once deployed, you can run the script repeatedly to maintain the virtualenv and update or add any distributions. 

The only dependency is python. You only need one file, virtualenv_deployer.py, which you can download here: https://raw.githubusercontent.com/dnut/virtualenv_deployer/master/virtualenv_deployer.py

Run it like this to create a basic virtualenv:
```sh
python virtualenv_deployer.py
```

## Automatically Distribution Installation
virtualenv_deployer will automatically install packages from a requirements file into your virtualenv. You can run it repeatedly as you update your requirements file and it will continue to update the virtualenv.

Make a requirements.txt file including the name of every distribution you want to install (local and remote), and if you have local distributions you want to install, put the wheels or any other format into a dependencies directory. If you use the name "requirements.txt" and "dependencies" for each of those respectively in your working directory, virtualenv_deployer will find them and install them automatically with the above command.

Alternatively, you can specify command line arguments for any of the optional paths: 
- dependencies directory (-d, --dependencies)
- requirements file (-r, --requirements)
- output destination directory (-o, --destination)

```sh
python virtualenv_deployer.py -d /path/to/dependencies_dir -r my_requirements.txt -o /path/to/venv/
```

## Ad Hoc Distribution Installation
You can also install any packages into the virtualenv on an ad hoc basis using the --pip-install (-i) command line option:
```sh
python virtualenv_deployer.py -i flask
```
This can be combined with any of the above options to install everything at once. When I deploy an app, I put all of its dependencies in requirements.txt, and use ```-i``` to install the app itself, all in a single command.

## Offline Installation
If you want to be able to deploy virtualenvs totally offline, then place all your dependencies (and their dependencies) in the dependencies folder. Also, for offline virtualenv deployments, you'll need to include the virtualenv zip, which you can download here: https://github.com/pypa/virtualenv/archive/16.0.0.zip

Then you can trigger the deployment like this:
```sh
python virtualenv_deployer.py -v 16.0.0.zip
```

## CLI Argument Summary

To view the help document for command line options, use this command:

```sh
python virtualenv_deployer.py -h
```
and here is the output:
```
usage: virtualenv_deployer.py [-h] [-y] [-o DESTINATION] [-d DEPENDENCIES]
                              [-r REQUIREMENTS] [-v VIRTUALENV_ZIP] [-i ...]
                              [--install-here]

optional arguments:
  -h, --help            show this help message and exit
  -y, --yes
  -o DESTINATION, --destination DESTINATION
  -d DEPENDENCIES, --dependencies DEPENDENCIES
  -r REQUIREMENTS, --requirements REQUIREMENTS
  -v VIRTUALENV_ZIP, --virtualenv-zip VIRTUALENV_ZIP
  -i ..., --pip-install ...
                        Run pip install <args> in the virtualenv. Only use
                        this option as the final option, because everything
                        following it will be assumed to be pip arguments.
  --install-here        Use this flag to indicate the script is being called
                        from within the virtualenv, and it should install
                        distributions directly into the calling python
                        installation.
```
