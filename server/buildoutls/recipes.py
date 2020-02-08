"""Registry of well-known recipes.

"""

from typing import Sequence, Dict, Set, Optional


class RecipeOption:
  """A Recipe option.
  """
  def __init__(
      self,
      documentation: str = "",
      valid_values: Sequence[str] = (),
  ):
    self.documentation = documentation

    self.valid_values = valid_values
    """Possible values. If this is empty, it means no constraint on values.
    """


class Recipe:
  """Information about a recipe.
  """
  def __init__(
      self,
      name: str = "",
      description: str = "",
      url: str = "",
      options: Optional[Dict[str, RecipeOption]] = None,
      generated_options: Optional[Dict[str, RecipeOption]] = None,
      required_options: Sequence[str] = (),
      template_options: Sequence[str] = (),
  ):
    self.name = name
    self.description = description
    self.url = url
    self.options: Dict[str, RecipeOption] = options or {}
    self.generated_options = generated_options or {}
    self.required_options: Set[str] = set(required_options)
    # Template options are filenames which are using buildout substitution.
    self.template_options: Set[str] = set(template_options)
    registry[self.name] = self

  @property
  def documentation(self) -> str:
    """Documentation of the recipe
    """
    return '## `{}`\n\n---\n{}'.format(self.name, self.description)


registry: Dict[str, Recipe] = {}

Recipe(
    name='slapos.recipe.template',
    description='Template recipe which supports remote resource.',
    url='https://pypi.org/project/slapos.recipe.template/',
    options={
        'url':
            RecipeOption('Url or path of the input template',),
        'output':
            RecipeOption('Path of the output',),
        'md5sum':
            RecipeOption('Check the integrity of the input file.',),
        'mode':
            RecipeOption(
                'Specify the filesystem permissions in octal notation.',),
    },
    required_options=('url', 'output'),
    template_options=('url',),
)

Recipe(
    name='slapos.recipe.template:jinja2',
    description='Template recipe which supports remote resource and templating with [jinja2](https://jinja.palletsprojects.com/en/2.10.x/)',
    url='https://pypi.org/project/slapos.recipe.template/',
    required_options=('template', 'rendered'),
    options={
        'template':
            RecipeOption(
                'Template url/path, as accepted by `zc.buildout.download.Download.__call__`. For very short template, it can make sense to put it directly into buildout.cfg: the value is the template itself, prefixed by the string `inline:` + an optional newline.',
            ),
        'rendered':
            RecipeOption('Where rendered template should be stored.',),
        'context':
            RecipeOption(
                """
  Jinja2 context specification, one variable per line, with 3 whitespace-separated parts:

 `type` `name` `expression`

 Available types are described below. name is the variable name to declare. Expression semantic varies depending on the type.

Available types:
	* `raw`: Immediate literal string.
	* `key`: Indirect literal string.
	* `import`: Import a python module.
	* `section`: Make a whole buildout section available to template, as a dictionary.

Indirection targets are specified as `[section]:key` . It is possible to use buildout’s built-in variable replacement instead instead of `key` type, but keep in mind that different lines are different variables for this recipe. It might be what you want (factorising context chunk declarations), otherwise you should use indirect types
""",),
        'md5sum':
            RecipeOption(
                "Template’s MD5, for file integrity checking. By default, no integrity check is done.",
            ),
        'mode':
            RecipeOption(
                "Mode, in octal representation (no need for 0-prefix) to set output file to. This is applied before storing anything in output file.",
            ),
        'once':
            RecipeOption(
                "Path of a marker file to prevents rendering altogether.",),
        'extensions':
            RecipeOption(
                "Jinja2 extensions to enable when rendering the template, whitespace-separated. By default, none is loaded.",
            ),
        'import-delimiter':
            RecipeOption(
                "Delimiter character for in-template imports. Defaults to `/`. See also: `import-list`",
            ),
        "import-list":
            RecipeOption(
                """Declares a list of import paths. Format is similar to context. `name` becomes import’s base name.

Available types:

	* `rawfile`: Literal path of a file.
	* `file`: Indirect path of a file.
	* `rawfolder`: Literal path of a folder. Any file in such folder can be imported.
	* `folder`: Indirect path of a folder. Any file in such folder can be imported.
	* `encoding`: Encoding for input template and output file. Defaults to `utf-8`.
""",),
    },
)

Recipe(
    name='slapos.recipe.build:gitclone',
    url='https://pypi.org/project/slapos.recipe.build/#id59',
    description='Checkout a git repository and its submodules by default. Supports `slapos.libnetworkcache` if present, and if boolean `use-cache` option is true.',
    required_options=('repository',),
    options={
        'repository':
            RecipeOption('URL of the git repository',),
        'branch':
            RecipeOption('Branch in the remote repository to check out',),
        'revision':
            RecipeOption(
                'Revision in the remote repository to check out. `revision` has priority over `branch`',
            ),
        'develop':
            RecipeOption(
                "Don't let buildout modify/delete this directory. By default, the checkout is managed by buildout, which means buildout will delete the working copy when option changes, if you don't want this, you can set `develop` to a true value. In that case, changes to buildout configuration will not be applied to working copy after intial checkout",
                valid_values=('true', 'false', 'yes', 'no'),
            ),
        'ignore-cloning-submodules':
            RecipeOption(
                'By default, cloning the repository will clone its submodules also. You can force git to ignore cloning submodules by defining `ignore-cloning-submodules` boolean option to true',
                valid_values=('true', 'false', 'yes', 'no'),
            ),
        'ignore-ssl-certificate':
            RecipeOption(
                'Ignore server certificate. By default, when remote server use SSL protocol git checks if the SSL certificate of the remote server is valid before executing commands. You can force git to ignore this check using ignore-ssl-certificate boolean option.',
                valid_values=('true', 'false', 'yes', 'no'),
            ),
        'git-command':
            RecipeOption('Full path to git command',),
        'shared':
            RecipeOption(
                "Clone with `--shared`  option if true. See  `git-clone` command.",
                valid_values=('true', 'false', 'yes', 'no'),
            ),
        'sparse-checkout':
            RecipeOption(
                "The value of the  sparse-checkout  option is written to the `$GITDIR/info/sparse-checkout` file, which is used to populate the working directory sparsely. See the *SPARSE CHECKOUT*  section of `git-read-tree` command. This feature is disabled if the value is empty or unset."
            ),
    },
    generated_options={
        'location':
            RecipeOption(
                'Path where to clone the repository, default to parts/${:_buildout_section_name_}',
            ),
    })

Recipe(
    'plone.recipe.command',
    url='https://pypi.org/project/plone.recipe.command/',
    description='The `plone.recipe.command` buildout recipe allows you to run a command when a buildout part is installed or updated.',
    required_options=('command',),
    options={
        'command':
            RecipeOption(
                'Command to run when the buildout part is installed.',),
        'update-command':
            RecipeOption(
                'Command to run when the buildout part is updated. This happens when buildout is run but the configuration for this buildout part has not changed.',
            ),
        'location':
            RecipeOption(
                '''A list of filesystem paths that buildout should consider as being managed by this buildout part.
These will be removed when buildout (re)installs or removes this part.''',),
        'stop-on-error':
            RecipeOption(
                'When `yes`, `on` or `true`, buildout will stop if the command ends with a non zero exit code.',
                valid_values=('true', 'yes'),
            ),
    },
)

Recipe(
    name='slapos.recipe.build',
    description='Deprectated, prefer slapos.recipe.cmmi which supports shared parts.',
    url='https://pypi.org/project/slapos.recipe.build/',
    generated_options={
        'location': RecipeOption('',),
    },
)

Recipe(
    name='slapos.recipe.cmmi',
    description='The recipe provides the means to compile and install source distributions using configure and make and other similar tools.',
    url='https://pypi.org/project/slapos.recipe.cmmi/',
    options={
        'url':
            RecipeOption(
                '''URL to the package that will be downloaded and extracted. The
supported package formats are `.tar.gz`, `.tar.bz2`, and `.zip`. The value must be a full URL,
e.g. http://python.org/ftp/python/2.4.4/Python-2.4.4.tgz. The `path` option can not be used at the same time with `url`.'''
            ),
        'path':
            RecipeOption(
                '''Path to a local directory containing the source code to be built
and installed. The directory must contain the `configure` script. The `url` option can not be used at the same time with `path`. '''
            ),
        'prefix':
            RecipeOption(
                '''Custom installation prefix passed to the `--prefix` option of the configure script. Defaults to the location of the part.
Note that this is a convenience shortcut which assumes that the default configure command is used to configure the package.
If the `configure-command` option is used to define a custom configure command no automatic `--prefix` injection takes place.
You can also set the `--prefix` parameter explicitly in `configure-options`.'''
            ),
        'shared':
            RecipeOption(
                '''Specify the path in which this package is shared by many other packages.
`shared-part-list` should be defined in `[buildout]` section
Shared option is True or False.
The package will be installed on `path/name/hash of options`.
''',
                valid_values=['true', 'false'],
            ),
        'md5sum':
            RecipeOption('''MD5 checksum for the package file.
If available the MD5 checksum of the downloaded package will be compared to this value and if the values do not match the execution of the recipe will fail.'''
                        ),
        'make-binary':
            RecipeOption(
                '''Path to the make program. Defaults to `make` which should work on any system that has the make program available in the system `PATH`.'''
            ),
        'make-options':
            RecipeOption(
                '''Extra `KEY=VALUE` options included in the invocation of the make program.
Multiple options can be given on separate lines to increase readability.'''),
        'make-targets':
            RecipeOption(
                '''Targets for the `make` command. Defaults to `install` which will be enough to install most software packages.
You only need to use this if you want to build alternate targets. Each target must be given on a separate line.'''
            ),
        'configure-command':
            RecipeOption(
                '''Name of the configure command that will be run to generate the Makefile.
This defaults to `./configure` which is fine for packages that come with a configure script.
You may wish to change this when compiling packages with a different set up.
See the *Compiling a Perl package* section for an example.'''),
        'configure-options':
            RecipeOption('''Extra options to be given to the configure script.
By default only the `--prefix` option is passed which is set to the part directory.
Each option must be given on a separate line.
'''),
        'patch-binary':
            RecipeOption('''Path to the `patch` program.
Defaults to `patch` which should work on any system that has the patch program available in the system `PATH`.'''
                        ),
        'patch-options':
            RecipeOption(
                '''Options passed to the `patch` program. Defaults to `-p0`.'''
            ),
        'patches':
            RecipeOption(
                '''List of patch files to the applied to the extracted source.
Each file should be given on a separate line.'''),
        'pre-configure-hook':
            RecipeOption(
                '''Custom python script that will be executed before running the configure script.
        
The format of the options is:
```
/path/to/the/module.py:name_of_callable
url:name_of_callable
url#md5sum:name_of_callable
````

where the first part is a filesystem path or url to the python
module and the second part is the name of the callable in the
module that will be called.  The callable will be passed three
parameters in the following order:

1. The options dictionary from the recipe.
2. The global buildout dictionary.
3. A dictionary containing the current os.environ augmented with the part specific overrides.


The callable is not expected to return anything.

*Note:*

The `os.environ` is not modified so if the hook script is
interested in the environment variable overrides defined for the
part it needs to read them from the dictionary that is passed in
as the third parameter instead of accessing os.environ
directly.
'''),
        'pre-make-hook':
            RecipeOption(
                '''Custom python script that will be executed before running `make`.
The format and semantics are the same as with the `pre-configure-hook option`.'''
            ),
        'post-make-hook':
            RecipeOption(
                '''Custom python script that will be executed after running `make`.
The format and semantics are the same as with the `pre-configure-hook` option.'''
            ),
        'pre-configure':
            RecipeOption(
                '''Shell command that will be executed before running `configure` script.
It takes the same effect as `pre-configure-hook` option except it's shell command.'''
            ),
        'pre-build':
            RecipeOption(
                '''Shell command that will be executed before running `make`.
It takes the same effect as `pre-make-hook` option except it's shell command.'''
            ),
        'pre-install':
            RecipeOption(
                '''Shell command that will be executed before running `make` install.'''
            ),
        'post-install':
            RecipeOption(
                '''Shell command that will be executed after running `make` install.
It takes the same effect as `post-make-hook` option except it's shell command.'''
            ),
        'keep-compile-dir':
            RecipeOption(
                '''Switch to optionally keep the temporary directory where the package was compiled.

This is mostly useful for other recipes that use this recipe to compile a software but wish to do some additional steps not handled by this recipe.

The location of the compile directory is stored in `options['compile-directory']`.

Accepted values are true or false, defaults to false.''',
                valid_values=['true', 'false'],
            ),
        'promises':
            RecipeOption(
                '''List the pathes and files should be existed after install part.
The file or path must be absolute path.
One line one item.
If any item doesn't exist, the recipe shows a warning message.
The default value is empty.'''),
        'dependencies':
            RecipeOption('''List all the depended parts:

```
dependencies = part1 part2 ...
```

All the dependent parts will be installed before this part, besides the changes in any dependent parts will trigger to reinstall current part.
         '''),
        'environment-section':
            RecipeOption(
                '''Name of a section that provides environment variables that will be used to
augment the variables read from `os.environ` before executing the
recipe.

This recipe does not modify `os.environ` directly. External commands
run as part of the recipe (e.g. `make`, `configure`, etc.) get an augmented
environment when they are forked. Python hook scripts are passed the
augmented as a parameter.
The values of the environment variables may contain references to other
existing environment variables (including themselves) in the form of
Python string interpolation variables using the dictionary notation. These
references will be expanded using values from `os.environ`. This can be
used, for example, to append to the `PATH` variable, e.g.:

```
[component]
recipe = slapos.recipe.cmmi
environment-section =
    environment

[environment]
PATH = %(PATH)s:${buildout:directory}/bin
```
         '''),
        'environment':
            RecipeOption(
                '''A sequence of `KEY=VALUE` pairs separated by newlines that define
additional environment variables used to update `os.environ` before
executing the recipe.

The semantics of this option are the same as `environment-section`. If
both `environment-section` and `environment` are provided the values from
the former will be overridden by the latter allowing per-part customization.
         '''),
    },
    generated_options={
        'location':
            RecipeOption(
                '''Location where the package is installed.

Defaults to `${buildout:parts-directory}/${:_buildout_section_name_}`,
or to ${buildout:shared-part-list[-1]}/${:_buildout_section_name_}/${option_hash} if `shared` was set to a true value.

This option is only available after part is installed, but to help resolve bootstrap
issues, the magic string `@@LOCATION@@` is also understood by this recipe as an alias
to the `location` option.
''',),
    },
)

Recipe(
    name='zc.recipe.egg',
    description='The `zc.recipe.egg:eggs` recipe can be used to install various types if distutils distributions as eggs.',
    url='https://pypi.org/project/zc.recipe.egg/',
    options={
        'eggs':
            RecipeOption(
                '''A list of eggs to install given as one or more setuptools requirement strings.
Each string must be given on a separate line.'''),
        'find-links':
            RecipeOption(
                '''A list of URLs, files, or directories to search for distributions.'''
            ),
        'index':
            RecipeOption(
                '''The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored.
'''),
    })

Recipe(
    name='zc.recipe.egg:eggs',
    description='The `zc.recipe.egg:eggs` recipe can be used to install various types if distutils distributions as eggs.',
    url='https://pypi.org/project/zc.recipe.egg/',
    options={
        'eggs':
            RecipeOption(
                '''A list of eggs to install given as one or more setuptools requirement strings.
Each string must be given on a separate line.'''),
        'find-links':
            RecipeOption(
                '''A list of URLs, files, or directories to search for distributions.'''
            ),
        'index':
            RecipeOption(
                '''The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored.
'''),
    })

for name in (
    'zc.recipe.egg',
    'zc.recipe.egg:script',
    'zc.recipe.egg:scripts',
):
  Recipe(
      name=name,
      description=f'The `{name}` recipe install python distributions as eggs',
      url='https://pypi.org/project/zc.recipe.egg/',
      options={
          'entry-points':
              RecipeOption('''A list of entry-point identifiers of the form:

```
name=module:attrs
```

where `name` is a script name, `module` is a dotted name resolving to a module name, and `attrs` is a dotted name resolving to a callable object within a module.

This option is useful when working with distributions that don’t declare entry points, such as distributions not written to work with setuptools.'''
                          ),
          'scripts':
              RecipeOption('''Control which scripts are generated.

The value should be a list of zero or more tokens.

Each token is either a name, or a name followed by an ‘=’ and a new name. Only the named scripts are generated.

If no tokens are given, then script generation is disabled.

If the option isn’t given at all, then all scripts defined by the named eggs will be generated.'''
                          ),
          'dependent-scripts':
              RecipeOption(
                  '''If set to the string “true”, scripts will be generated for all required eggs in addition to the eggs specifically named.''',
                  valid_values=['true', 'false']),
          'interpreter':
              RecipeOption(
                  '''The name of a script to generate that allows access to a Python interpreter that has the path set based on the eggs installed.'''
              ),
          'extra-paths':
              RecipeOption('''Extra paths to include in a generated script.'''),
          'initialization':
              RecipeOption('''Specify some Python initialization code.
This is very limited. 

In particular, be aware that leading whitespace is stripped from the code given.'''
                          ),
          'arguments':
              RecipeOption(
                  '''Specify some arguments to be passed to entry points as Python source.'''
              ),
          'relative-paths':
              RecipeOption(
                  '''If set to true, then egg paths will be generated relative to the script path.

This allows a buildout to be moved without breaking egg paths.

This option can be set in either the script section or in the buildout section.
''',
                  valid_values=['true', 'false']),
          'egg':
              RecipeOption(
                  '''An specification for the egg to be created, to install given as a setuptools requirement string.
        
This defaults to the part name.'''),
          'eggs':
              RecipeOption(
                  '''A list of eggs to install given as one or more setuptools requirement strings.
Each string must be given on a separate line.'''),
          'find-links':
              RecipeOption(
                  '''A list of URLs, files, or directories to search for distributions.'''
              ),
          'index':
              RecipeOption(
                  '''The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored.
'''),
      })

Recipe(
    name='zc.recipe.egg:custom',
    description='The `zc.recipe.egg:custom` recipe can be used to install an egg with custom build parameters.',
    url='https://pypi.org/project/zc.recipe.egg/',
    options={
        'include-dirs':
            RecipeOption(
                '''A new-line separated list of directories to search for include files.'''
            ),
        'library-dirs':
            RecipeOption(
                '''A new-line separated list of directories to search for libraries to link with.'''
            ),
        'rpath':
            RecipeOption(
                '''A new-line separated list of directories to search for dynamic libraries at run time.'''
            ),
        'define':
            RecipeOption(
                '''A comma-separated list of names of C preprocessor variables to define.'''
            ),
        'undef':
            RecipeOption(
                '''A comma-separated list of names of C preprocessor variables to undefine.'''
            ),
        'libraries':
            RecipeOption('''The name of an additional library to link with.
Due to limitations in distutils and despite the option name, only a single library can be specified.'''
                        ),
        'link-objects':
            RecipeOption('''The name of an link object to link against.
Due to limitations in distutils and despite the option name, only a single link object can be specified.'''
                        ),
        'debug':
            RecipeOption('''Compile/link with debugging information'''),
        'force':
            RecipeOption(
                '''Forcibly build everything (ignore file timestamps)'''),
        'compiler':
            RecipeOption('''Specify the compiler type'''),
        'swig':
            RecipeOption('''The path to the swig executable'''),
        'swig-cpp':
            RecipeOption('''Make SWIG create C++ files (default is C)'''),
        'swig-opts':
            RecipeOption('''List of SWIG command line options'''),
        'egg':
            RecipeOption(
                '''An specification for the egg to be created, to install given as a setuptools requirement string.
This defaults to the part name.'''),
        'find-links':
            RecipeOption(
                '''A list of URLs, files, or directories to search for distributions.'''
            ),
        'index':
            RecipeOption(
                '''The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored.'''
            ),
        'environment':
            RecipeOption(
                '''The name of a section with additional environment variables.
The environment variables are set before the egg is built.'''),
    })

Recipe(
    name='zc.recipe.egg:develop',
    description='''The `zc.recipe.egg:develop` recipe can be used to make a path containing source available as an installation candidate.

It does not install the egg, another `zc.recipe.egg` section will be needed for this.''',
    url='https://pypi.org/project/zc.recipe.egg/',
    options={
        'setup':
            RecipeOption(
                'The path to a setup script or directory containing a startup script. This is required'
            )
    })
