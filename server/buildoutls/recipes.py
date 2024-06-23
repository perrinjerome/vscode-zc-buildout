"""Registry of well-known recipes."""

from typing import Dict, Optional, Sequence, Set

import enum


class RecipeOptionKind(enum.Enum):
  Text = enum.auto()
  ShellScript = enum.auto()
  PythonScript = enum.auto()


class RecipeOption:
  """A Recipe option."""

  def __init__(
    self,
    documentation: str = "",
    valid_values: Sequence[str] = (),
    deprecated: Optional[str] = "",
    kind: Optional[RecipeOptionKind] = RecipeOptionKind.Text,
  ):
    self.documentation = documentation

    self.valid_values = valid_values
    """Possible values. If this is empty, it means no constraint on values.
    """
    self.deprecated = deprecated
    """Reason for the option to be deprected, if it is deprecated.
    """
    self.kind = kind
    """Type of the option.
    """


class Recipe:
  """Information about a recipe."""

  def __init__(
    self,
    name: str = "",
    description: str = "",
    url: str = "",
    options: Optional[Dict[str, RecipeOption]] = None,
    generated_options: Optional[Dict[str, RecipeOption]] = None,
    required_options: Sequence[str] = (),
    template_options: Sequence[str] = (),
    any_options: bool = False,
  ):
    self.name = name
    self.description = description
    self.url = url
    self.options: Dict[str, RecipeOption] = options or {}
    self.generated_options = generated_options or {}
    self.required_options: Set[str] = set(required_options)
    # Template options are filenames which are using buildout substitution.
    self.template_options: Set[str] = set(template_options)
    # Flag for recipe which can generates arbitrary options. If true, we can
    # not know if referenced options exist or not during diagnostics.
    self.any_options = any_options
    registry[self.name] = self

  @property
  def documentation(self) -> str:
    """Documentation of the recipe"""
    return "## `{}`\n\n---\n{}".format(self.name, self.description)


registry: Dict[str, Recipe] = {}

Recipe(
  name="slapos.recipe.template",
  description="Template recipe which supports remote resource.",
  url="https://pypi.org/project/slapos.recipe.template/",
  options={
    "url": RecipeOption(
      "Url or path of the input template",
    ),
    "inline": RecipeOption(
      "Inline input template",
    ),
    "output": RecipeOption(
      "Path of the output",
    ),
    "md5sum": RecipeOption(
      "Check the integrity of the input file.",
    ),
    "mode": RecipeOption(
      "Specify the filesystem permissions in octal notation.",
    ),
  },
  required_options=("url", "output"),
  template_options=("url",),
)

Recipe(
  name="slapos.recipe.template:jinja2",
  description="Template recipe which supports remote resource and templating with [jinja2](https://jinja.palletsprojects.com/en/2.10.x/)",
  url="https://pypi.org/project/slapos.recipe.template/",
  required_options=("url", "output"),
  options={
    "url": RecipeOption(
      "Url or path of the input template",
    ),
    "inline": RecipeOption(
      "Inline input template",
    ),
    "output": RecipeOption(
      "Path of the output",
    ),
    "template": RecipeOption(
      "Template url/path, as accepted by `zc.buildout.download.Download.__call__`. For very short template, it can make sense to put it directly into buildout.cfg: the value is the template itself, prefixed by the string `inline:` + an optional newline.",
      deprecated="Use `url` or `inline` options instead",
    ),
    "rendered": RecipeOption(
      "Where rendered template should be stored.",
      deprecated="Use `output` option instead",
    ),
    "context": RecipeOption(
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
""",
    ),
    "md5sum": RecipeOption(
      "Template’s MD5, for file integrity checking. By default, no integrity check is done.",
    ),
    "mode": RecipeOption(
      "Mode, in octal representation (no need for 0-prefix) to set output file to. This is applied before storing anything in output file.",
    ),
    "once": RecipeOption(
      "Path of a marker file to prevents rendering altogether.",
    ),
    "extensions": RecipeOption(
      "Jinja2 extensions to enable when rendering the template, whitespace-separated. By default, none is loaded.",
    ),
    "import-delimiter": RecipeOption(
      "Delimiter character for in-template imports. Defaults to `/`. See also: `import-list`",
    ),
    "import-list": RecipeOption(
      """Declares a list of import paths. Format is similar to context. `name` becomes import’s base name.

Available types:

  * `rawfile`: Literal path of a file.
  * `file`: Indirect path of a file.
  * `rawfolder`: Literal path of a folder. Any file in such folder can be imported.
  * `folder`: Indirect path of a folder. Any file in such folder can be imported.
  * `encoding`: Encoding for input template and output file. Defaults to `utf-8`.
""",
    ),
  },
)

Recipe(
  name="slapos.recipe.build:gitclone",
  url="https://pypi.org/project/slapos.recipe.build/#id59",
  description="Checkout a git repository and its submodules by default. Supports `slapos.libnetworkcache` if present, and if boolean `use-cache` option is true.",
  required_options=("repository",),
  options={
    "repository": RecipeOption(
      "URL of the git repository",
    ),
    "branch": RecipeOption(
      "Branch in the remote repository to check out",
    ),
    "revision": RecipeOption(
      "Revision in the remote repository to check out. `revision` has priority over `branch`",
    ),
    "develop": RecipeOption(
      "Don't let buildout modify/delete this directory. By default, the checkout is managed by buildout, which means buildout will delete the working copy when option changes, if you don't want this, you can set `develop` to a true value. In that case, changes to buildout configuration will not be applied to working copy after intial checkout",
      valid_values=("true", "false", "yes", "no"),
    ),
    "ignore-cloning-submodules": RecipeOption(
      "By default, cloning the repository will clone its submodules also. You can force git to ignore cloning submodules by defining `ignore-cloning-submodules` boolean option to true",
      valid_values=("true", "false", "yes", "no"),
    ),
    "ignore-ssl-certificate": RecipeOption(
      "Ignore server certificate. By default, when remote server use SSL protocol git checks if the SSL certificate of the remote server is valid before executing commands. You can force git to ignore this check using ignore-ssl-certificate boolean option.",
      valid_values=("true", "false", "yes", "no"),
    ),
    "git-command": RecipeOption(
      "Full path to git command",
    ),
    "shared": RecipeOption(
      "Clone with `--shared`  option if true. See  `git-clone` command.",
      valid_values=("true", "false", "yes", "no"),
    ),
    "sparse-checkout": RecipeOption(
      "The value of the  sparse-checkout  option is written to the `$GITDIR/info/sparse-checkout` file, which is used to populate the working directory sparsely. See the *SPARSE CHECKOUT*  section of `git-read-tree` command. This feature is disabled if the value is empty or unset."
    ),
  },
  generated_options={
    "location": RecipeOption(
      "Path where to clone the repository, default to parts/${:_buildout_section_name_}",
    ),
  },
)

Recipe(
  "plone.recipe.command",
  url="https://pypi.org/project/plone.recipe.command/",
  description="The `plone.recipe.command` buildout recipe allows you to run a command when a buildout part is installed or updated.",
  required_options=("command",),
  options={
    "command": RecipeOption(
      "Command to run when the buildout part is installed.",
      kind=RecipeOptionKind.ShellScript,
    ),
    "update-command": RecipeOption(
      "Command to run when the buildout part is updated. This happens when buildout is run but the configuration for this buildout part has not changed.",
      kind=RecipeOptionKind.ShellScript,
    ),
    "location": RecipeOption(
      """A list of filesystem paths that buildout should consider as being managed by this buildout part.
These will be removed when buildout (re)installs or removes this part.""",
    ),
    "stop-on-error": RecipeOption(
      "When `yes`, `on` or `true`, buildout will stop if the command ends with a non zero exit code.",
      valid_values=("true", "yes"),
    ),
  },
)

Recipe(
  name="slapos.recipe.build:download",
  description="""Download a file
    """,
  url="https://pypi.org/project/slapos.recipe.build/",
  options={
    "url": RecipeOption(
      "URL to download from",
    ),
    "md5sum": RecipeOption(
      "Checksum of the download",
    ),
    "offline": RecipeOption(
      "Override buildout global ``offline`` setting for the context of this section",
      valid_values=("true", "false"),
    ),
    "filename": RecipeOption(
      "",
    ),
  },
  generated_options={
    "location": RecipeOption(
      "",
    ),
    "target": RecipeOption(
      "",
    ),
  },
  required_options=(
    "url",
    "md5sum",
  ),
)

Recipe(
  name="slapos.recipe.build:download-unpacked",
  description="""Download an archive and unpack it
    """,
  url="https://pypi.org/project/slapos.recipe.build/",
  options={
    "url": RecipeOption(
      "URL to download from",
    ),
    "md5sum": RecipeOption(
      "Checksum of the download",
    ),
    "offline": RecipeOption(
      "Override buildout global ``offline`` setting for the context of this section",
      valid_values=("true", "false"),
    ),
    "filename": RecipeOption(
      "",
    ),
    "strip-top-level-dir": RecipeOption("", valid_values=("true", "false")),
  },
  generated_options={
    "location": RecipeOption(
      "",
    ),
    "target": RecipeOption(
      "",
    ),
  },
  required_options=(
    "url",
    "md5sum",
  ),
)

Recipe(
  name="slapos.recipe.build",
  description="""Generally deprecated in favor slapos.recipe.cmmi, which supports shared parts,
    but useful for corner cases as it allows inline python code.
    """,
  url="https://pypi.org/project/slapos.recipe.build/",
  options={
    "init": RecipeOption(
      "python code executed at initialization step",
      kind=RecipeOptionKind.PythonScript,
    ),
    "install": RecipeOption(
      "python code executed at install step",
      kind=RecipeOptionKind.PythonScript,
    ),
    "update": RecipeOption(
      "python code executed when updating",
      kind=RecipeOptionKind.PythonScript,
    ),
  },
  generated_options={
    "location": RecipeOption(
      "",
    ),
  },
  any_options=True,
)

Recipe(
  name="slapos.recipe.cmmi",
  description="The recipe provides the means to compile and install source distributions using configure and make and other similar tools.",
  url="https://pypi.org/project/slapos.recipe.cmmi/",
  options={
    "url": RecipeOption(
      """URL to the package that will be downloaded and extracted. The
supported package formats are `.tar.gz`, `.tar.bz2`, and `.zip`. The value must be a full URL,
e.g. http://python.org/ftp/python/2.4.4/Python-2.4.4.tgz. The `path` option can not be used at the same time with `url`."""
    ),
    "path": RecipeOption(
      """Path to a local directory containing the source code to be built
and installed. The directory must contain the `configure` script. The `url` option can not be used at the same time with `path`. """
    ),
    "prefix": RecipeOption(
      """Custom installation prefix passed to the `--prefix` option of the configure script. Defaults to the location of the part.
Note that this is a convenience shortcut which assumes that the default configure command is used to configure the package.
If the `configure-command` option is used to define a custom configure command no automatic `--prefix` injection takes place.
You can also set the `--prefix` parameter explicitly in `configure-options`."""
    ),
    "shared": RecipeOption(
      """Specify the path in which this package is shared by many other packages.
`shared-part-list` should be defined in `[buildout]` section
Shared option is True or False.
The package will be installed on `path/name/hash of options`.
""",
      valid_values=["true", "false"],
    ),
    "md5sum": RecipeOption("""MD5 checksum for the package file.
If available the MD5 checksum of the downloaded package will be compared to this value and if the values do not match the execution of the recipe will fail."""),
    "make-binary": RecipeOption(
      """Path to the make program. Defaults to `make` which should work on any system that has the make program available in the system `PATH`."""
    ),
    "make-options": RecipeOption(
      """Extra `KEY=VALUE` options included in the invocation of the make program.
Multiple options can be given on separate lines to increase readability."""
    ),
    "make-targets": RecipeOption(
      """Targets for the `make` command. Defaults to `install` which will be enough to install most software packages.
You only need to use this if you want to build alternate targets. Each target must be given on a separate line."""
    ),
    "configure-command": RecipeOption(
      """Name of the configure command that will be run to generate the Makefile.
This defaults to `./configure` which is fine for packages that come with a configure script.
You may wish to change this when compiling packages with a different set up.
See the *Compiling a Perl package* section for an example.""",
      kind=RecipeOptionKind.ShellScript,
    ),
    "configure-options": RecipeOption("""Extra options to be given to the configure script.
By default only the `--prefix` option is passed which is set to the part directory.
Each option must be given on a separate line.
"""),
    "patch-binary": RecipeOption("""Path to the `patch` program.
Defaults to `patch` which should work on any system that has the patch program available in the system `PATH`."""),
    "patch-options": RecipeOption(
      """Options passed to the `patch` program. Defaults to `-p0`."""
    ),
    "patches": RecipeOption(
      """List of patch files to the applied to the extracted source.
Each file should be given on a separate line."""
    ),
    "pre-configure-hook": RecipeOption(
      """Custom python script that will be executed before running the configure script.
        
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
"""
    ),
    "pre-make-hook": RecipeOption(
      """Custom python script that will be executed before running `make`.
The format and semantics are the same as with the `pre-configure-hook option`."""
    ),
    "post-make-hook": RecipeOption(
      """Custom python script that will be executed after running `make`.
The format and semantics are the same as with the `pre-configure-hook` option."""
    ),
    "pre-configure": RecipeOption(
      """Shell command that will be executed before running `configure` script.
It takes the same effect as `pre-configure-hook` option except it's shell command.""",
      kind=RecipeOptionKind.ShellScript,
    ),
    "pre-build": RecipeOption(
      """Shell command that will be executed before running `make`.
It takes the same effect as `pre-make-hook` option except it's shell command.""",
      kind=RecipeOptionKind.ShellScript,
    ),
    "pre-install": RecipeOption(
      """Shell command that will be executed before running `make` install.""",
      kind=RecipeOptionKind.ShellScript,
    ),
    "post-install": RecipeOption(
      """Shell command that will be executed after running `make` install.
It takes the same effect as `post-make-hook` option except it's shell command.""",
      kind=RecipeOptionKind.ShellScript,
    ),
    "keep-compile-dir": RecipeOption(
      """Switch to optionally keep the temporary directory where the package was compiled.

This is mostly useful for other recipes that use this recipe to compile a software but wish to do some additional steps not handled by this recipe.

The location of the compile directory is stored in `options['compile-directory']`.

Accepted values are true or false, defaults to false.""",
      valid_values=["true", "false"],
    ),
    "promises": RecipeOption(
      """List the pathes and files should be existed after install part.
The file or path must be absolute path.
One line one item.
If any item doesn't exist, the recipe shows a warning message.
The default value is empty."""
    ),
    "dependencies": RecipeOption("""List all the depended parts:

```
dependencies = part1 part2 ...
```

All the dependent parts will be installed before this part, besides the changes in any dependent parts will trigger to reinstall current part.
         """),
    "environment-section": RecipeOption(
      """Name of a section that provides environment variables that will be used to
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
         """
    ),
    "environment": RecipeOption(
      """A sequence of `KEY=VALUE` pairs separated by newlines that define
additional environment variables used to update `os.environ` before
executing the recipe.

The semantics of this option are the same as `environment-section`. If
both `environment-section` and `environment` are provided the values from
the former will be overridden by the latter allowing per-part customization.
         """
    ),
  },
  generated_options={
    "location": RecipeOption(
      """Location where the package is installed.

Defaults to `${buildout:parts-directory}/${:_buildout_section_name_}`,
or to ${buildout:shared-part-list[-1]}/${:_buildout_section_name_}/${option_hash} if `shared` was set to a true value.

This option is only available after part is installed, but to help resolve bootstrap
issues, the magic string `@@LOCATION@@` is also understood by this recipe as an alias
to the `location` option.
""",
    ),
  },
)

Recipe(
  name="zc.recipe.egg",
  description="The `zc.recipe.egg:eggs` recipe can be used to install various types if distutils distributions as eggs.",
  url="https://pypi.org/project/zc.recipe.egg/",
  options={
    "eggs": RecipeOption(
      """A list of eggs to install given as one or more setuptools requirement strings.
Each string must be given on a separate line."""
    ),
    "find-links": RecipeOption(
      """A list of URLs, files, or directories to search for distributions."""
    ),
    "index": RecipeOption(
      """The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored.
"""
    ),
  },
)

Recipe(
  name="zc.recipe.egg:eggs",
  description="The `zc.recipe.egg:eggs` recipe can be used to install various types if distutils distributions as eggs.",
  url="https://pypi.org/project/zc.recipe.egg/",
  options={
    "eggs": RecipeOption(
      """A list of eggs to install given as one or more setuptools requirement strings.
Each string must be given on a separate line."""
    ),
    "find-links": RecipeOption(
      """A list of URLs, files, or directories to search for distributions."""
    ),
    "index": RecipeOption(
      """The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored.
"""
    ),
  },
)

for name in (
  "zc.recipe.egg",
  "zc.recipe.egg:script",
  "zc.recipe.egg:scripts",
):
  Recipe(
    name=name,
    description=f"The `{name}` recipe install python distributions as eggs",
    url="https://pypi.org/project/zc.recipe.egg/",
    options={
      "entry-points": RecipeOption("""A list of entry-point identifiers of the form:

```
name=module:attrs
```

where `name` is a script name, `module` is a dotted name resolving to a module name, and `attrs` is a dotted name resolving to a callable object within a module.

This option is useful when working with distributions that don’t declare entry points, such as distributions not written to work with setuptools."""),
      "scripts": RecipeOption("""Control which scripts are generated.

The value should be a list of zero or more tokens.

Each token is either a name, or a name followed by an ‘=’ and a new name. Only the named scripts are generated.

If no tokens are given, then script generation is disabled.

If the option isn’t given at all, then all scripts defined by the named eggs will be generated."""),
      "dependent-scripts": RecipeOption(
        """If set to the string “true”, scripts will be generated for all required eggs in addition to the eggs specifically named.""",
        valid_values=["true", "false"],
      ),
      "interpreter": RecipeOption(
        """The name of a script to generate that allows access to a Python interpreter that has the path set based on the eggs installed."""
      ),
      "extra-paths": RecipeOption("""Extra paths to include in a generated script."""),
      "initialization": RecipeOption(
        """Specify some Python initialization code.
This is very limited. 

In particular, be aware that leading whitespace is stripped from the code given.""",
        kind=RecipeOptionKind.PythonScript,
      ),
      "arguments": RecipeOption(
        """Specify some arguments to be passed to entry points as Python source."""
      ),
      "relative-paths": RecipeOption(
        """If set to true, then egg paths will be generated relative to the script path.

This allows a buildout to be moved without breaking egg paths.

This option can be set in either the script section or in the buildout section.
""",
        valid_values=["true", "false"],
      ),
      "egg": RecipeOption(
        """An specification for the egg to be created, to install given as a setuptools requirement string.
        
This defaults to the part name."""
      ),
      "eggs": RecipeOption(
        """A list of eggs to install given as one or more setuptools requirement strings.
Each string must be given on a separate line."""
      ),
      "find-links": RecipeOption(
        """A list of URLs, files, or directories to search for distributions."""
      ),
      "index": RecipeOption(
        """The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored.
"""
      ),
    },
  )

Recipe(
  name="zc.recipe.egg:custom",
  description="The `zc.recipe.egg:custom` recipe can be used to install an egg with custom build parameters.",
  url="https://pypi.org/project/zc.recipe.egg/",
  options={
    "include-dirs": RecipeOption(
      """A new-line separated list of directories to search for include files."""
    ),
    "library-dirs": RecipeOption(
      """A new-line separated list of directories to search for libraries to link with."""
    ),
    "rpath": RecipeOption(
      """A new-line separated list of directories to search for dynamic libraries at run time."""
    ),
    "define": RecipeOption(
      """A comma-separated list of names of C preprocessor variables to define."""
    ),
    "undef": RecipeOption(
      """A comma-separated list of names of C preprocessor variables to undefine."""
    ),
    "libraries": RecipeOption("""The name of an additional library to link with.
Due to limitations in distutils and despite the option name, only a single library can be specified."""),
    "link-objects": RecipeOption("""The name of an link object to link against.
Due to limitations in distutils and despite the option name, only a single link object can be specified."""),
    "debug": RecipeOption("""Compile/link with debugging information"""),
    "force": RecipeOption("""Forcibly build everything (ignore file timestamps)"""),
    "compiler": RecipeOption("""Specify the compiler type"""),
    "swig": RecipeOption("""The path to the swig executable"""),
    "swig-cpp": RecipeOption("""Make SWIG create C++ files (default is C)"""),
    "swig-opts": RecipeOption("""List of SWIG command line options"""),
    "egg": RecipeOption(
      """An specification for the egg to be created, to install given as a setuptools requirement string.
This defaults to the part name."""
    ),
    "find-links": RecipeOption(
      """A list of URLs, files, or directories to search for distributions."""
    ),
    "index": RecipeOption(
      """The URL of an index server, or almost any other valid URL. :)

If not specified, the Python Package Index, https://pypi.org/simple, is used.

You can specify an alternate index with this option.
If you use the links option and if the links point to the needed distributions, then the index can be anything and will be largely ignored."""
    ),
    "environment": RecipeOption(
      """The name of a section with additional environment variables.
The environment variables are set before the egg is built."""
    ),
  },
)

Recipe(
  name="zc.recipe.egg:develop",
  description="""The `zc.recipe.egg:develop` recipe can be used to make a path containing source available as an installation candidate.

It does not install the egg, another `zc.recipe.egg` section will be needed for this.""",
  url="https://pypi.org/project/zc.recipe.egg/",
  options={
    "setup": RecipeOption(
      "The path to a setup script or directory containing a startup script. This is required"
    )
  },
)

Recipe(
  name="slapos.cookbook:wrapper",
  description="""Recipe to create a script from given command and options.
    """,
  url="https://lab.nexedi.com/nexedi/slapos/",
  options={
    "command-line": RecipeOption("shell command which launches the intended process"),
    "wrapper-path": RecipeOption("absolute path to file's destination"),
    "wait-for-files": RecipeOption("list of files to wait for"),
    "hash-files": RecipeOption(
      "list of buildout-generated files to be checked by hash"
    ),
    "hash-existing-files": RecipeOption("list of existing files to be checked by hash"),
    "pidfile": RecipeOption("path to pidfile ensure exclusivity for the process"),
    "private-tmpfs": RecipeOption(
      'list of "<size> <path>" private tmpfs, using user namespaces'
    ),
    "reserve-cpu": RecipeOption(
      "Command will ask for an exclusive CPU core",
    ),
  },
  required_options=("command-line", "wrapper-path"),
)


Recipe(
  name="plone.recipe.zope2instance",
  url="https://pypi.org/project/plone.recipe.zope2instance/",
  description="""The `plone.recipe.zope2instance` is a recipe to setup and configure a Zope 2 instance.

This recipe creates and configures a Zope instance in parts. (Despite its name it nowadays only works for Zope 4+.) It also installs a control script, which is like zopectl, in the bin/ directory. The name of the control script is the name of the part in buildout. By default various runtime and log information will be stored inside the var/ directory.

You can use it with a part like this:

    [instance]
    recipe = plone.recipe.zope2instance
    user = admin:admin
    http-address = 8080
    eggs = my.distribution
    zcml = my.distribution
""",
  required_options=("eggs",),
  options={
    "user": RecipeOption(
      "Manager user and password in `user:password` format.",
    ),
    "eggs": RecipeOption(
      "The list of distributions you want to make available to the instance.",
    ),
    "zcml": RecipeOption("""
Install ZCML slugs for the distributions listed, separated by whitespace. You
can specify the type of slug by appending '-' and the type of slug you want
to create. Some examples: ``my.distribution`` ``my.distribution-meta``.
"""),
    "http-address": RecipeOption("""
Set the address of the HTTP server.
Can be either a port or a socket address.
Defaults to 0.0.0.0:8080.
"""),
    "ip-address": RecipeOption(
      """
The default IP address on which Zope's various server protocol
implementations will listen for requests. If this is unset, Zope will listen
on all IP addresses supported by the machine. This directive can be
overridden on a per-server basis in the servers section. Defaults to not
setting an ip-address. Used for ZServer only, not WSGI.
""",
    ),
    "threads": RecipeOption("""
Specify the number of worker threads used to service requests.
The default is 4 for WSGI (since this is the waitress default) and 2 for ZServer.
"""),
    "zodb-cache-size": RecipeOption("""
Set the ZODB cache size, i.e. the number of objects which the ZODB cache
will try to hold. Defaults to 30000.
"""),
    "zserver-threads": RecipeOption(
      """
Deprecated, use `threads` instead.
Specify the number of threads that Zope's ZServer web server will use to
service requests. The recipes default is 2. Used for ZServer only, not WSGI.
""",
      deprecated="use `threads` instead.",
    ),
    "environment-vars": RecipeOption(
      """
Define arbitrary key-value pairs for use as environment variables during
Zope's run cycle. Example::

    environment-vars =
      TZ US/Eastern
      zope_i18n_allowed_languages en
      zope_i18n_compile_mo_files true

    """
    ),
    "initialization": RecipeOption(
      """
Specify some Python initialization code to include within the generated
``sitecustomize.py`` script (Buildout >= 1.5) or within the instance script
(Buildout < 1.5). This is very limited. In particular, be aware that leading
whitespace is stripped from the code given. *added in version 4.2.14*
""",
      kind=RecipeOptionKind.PythonScript,
    ),
    "wsgi": RecipeOption(
      """
By default this recipe creates a Python script that uses ``waitress`` as a
WSGI server. When running Python 2 you can disable WSGI and use ZServer by
setting ``wsgi = off`` and including ZServer in the ``eggs`` specification
list. Example::

  wsgi = off
  eggs =
    ...
    ZServer

You can use other PasteDeploy-compatible WSGI servers by passing a path
to a WSGI configuration file here and including the WSGI server's egg in the
``eggs`` specification. Example::

  wsgi = ${buildout:directory}/etc/gunicorn.ini
  eggs =
    ...
    gunicorn

The WSGI configuration file will not be created for you in this case,
unlike the built-in ``waitress`` support. You have to provide it yourself.
"""
    ),
    "max-request-body-size": RecipeOption(
      """
Specify the maximum request body size in bytes
The default is 1073741824 (since this is the waitress default)
"""
    ),
    "resources": RecipeOption(
      """
  Specify a central resource directory. Example::

    resources = ${buildout:directory}/resources
"""
    ),
    "locales": RecipeOption(
      """
Specify a locales directory. Example::

    locales = ${buildout:directory}/locales

This registers a locales directory with extra or different translations.
If you want to override a few translations from the `plone` domain in the
English language, you can add a ``en/LC_MESSAGES/plone.po`` file in this
directory, with standard headers at the top, followed by something like
this

  #. Default: "You are here:"
  msgid "you_are_here"
  msgstr "You are very welcome here:"

Translations for other message ids are not affected and will continue
to work.
"""
    ),
    "verbose-security": RecipeOption(
      """
  Set to `on` to turn on verbose security (and switch to the Python security
  implementation). Defaults to `off` (and the C security implementation).
"""
    ),
    "debug-exceptions": RecipeOption(
      """
WSGI only: set to ``on`` to disable exception views including
``standard_error_message``. Exceptions other than ``Unauthorized`` or
``ConflictError`` can then travel up into the WSGI stack. Use this option
if you want more convenient error debugging offered by WSGI middleware
such as the `werkzeug debugger
<https://werkzeug.palletsprojects.com/en/0.15.x/debug/>`_. See the `Zope
WSGI documentation <https://zope.readthedocs.io/en/latest/wsgi.html>`_ for
examples.
"""
    ),
    "profile": RecipeOption(
      """
Set to ``on`` enables `repoze.profile <https://github.com/repoze/repoze.profile>`_.
Defaults to ``off``,
If switched on there are further options prefixed with ``profile_`` to configure it as below.
You will need to add the `repoze.profile` package, either by adding it to your eggs section directly or by using the extra `plone.recipe.zope2instance[profile]`.
"""
    ),
    "profile_log_filename": RecipeOption(
      """
Filename of the raw profile data.
Default to ``profile-SECTIONNAME.raw``.
This file contains the raw profile data for further analysis.
""",
    ),
    "profile_cachegrind_filename": RecipeOption(
      """
If the package ``pyprof2calltree`` is installed, another file is written.
It is meant for consumation with any cachegrind compatible application.
Defaults to ``cachegrind.out.SECTIONNAME``.
"""
    ),
    "profile_discard_first_request": RecipeOption(
      """
  Defaults to ``true``.
  See `repoze.profile docs <https://repozeprofile.readthedocs.io/en/latest/#configuration-via-python>`_ for details.
""",
    ),
    "profile_path": RecipeOption(
      """
Defaults to ``/__profile__``.
The path for through the web access to the last profiled request.
""",
    ),
    "profile_flush_at_shutdown": RecipeOption(
      """ 
Defaults to ``true``.
See `repoze.profile docs <https://repozeprofile.readthedocs.io/en/latest/#configuration-via-python>`_ for details.
""",
    ),
    "profile_unwind": RecipeOption(
      """
Defaults to ``false``.
See `repoze.profile docs <https://repozeprofile.readthedocs.io/en/latest/#configuration-via-python>`_ for details.

If you have only one application process, it can open the database files
directly without running a database server process.
""",
    ),
    "file-storage": RecipeOption(
      """ 
The filename where the ZODB data file will be stored.
Defaults to `${buildout:directory}/var/filestorage/Data.fs`.
""",
    ),
    "blob-storage": RecipeOption(
      """

## With filestorage
                                 
The name of the directory where the ZODB blob data will be stored, defaults
to `${buildout:directory}/var/blobstorage`.

## With ZEO

The location of the blob zeocache, defaults to `var/blobcache`. If
`shared-blob` is on it defaults to `${buildout:directory}/var/blobstorage`.

"""
    ),
    "zeo-address": RecipeOption(
      """
Set the address of the ZEO server. Defaults to 8100. You can set
more than one address (white space delimited). Alternative addresses will
be used if the primary address is down.
""",
    ),
    "zeo-client": RecipeOption(
      """
Set to 'on' to make this instance a ZEO client. In this case, setting the
zeo-address option is required, and the file-storage option has no effect.
To set up a ZEO server, you can use the plone.recipe.zeoserver recipe.
Defaults to 'off'.
""",
    ),
    "shared-blob": RecipeOption(
      """
Defaults to `off`. Set this to `on` if the ZEO server and the instance have
access to the same directory. Either by being on the same physical machine or
by virtue of a network file system like NFS. Make sure this instances
`blob-storage` is set to the same directory used for the ZEO servers
`blob-storage`. In this case the instance will not stream the blob file
through the ZEO connection, but just send the information of the file
location to the ZEO server, resulting in faster execution and less memory
overhead.
""",
    ),
    "zeo-client-read-only-fallback": RecipeOption(
      """
A flag indicating whether a read-only remote storage should be acceptable as
a fallback when no writable storages are available. Defaults to false.
""",
    ),
    "read-only": RecipeOption(
      "Set zeo client as read only *added in version 4.2.12*",
    ),
    "zeo-username": RecipeOption(
      """
Enable ZEO authentication and use the given username when accessing the
ZEO server. It is obligatory to also specify a zeo-password.
""",
    ),
    "zeo-password": RecipeOption(
      """
Password to use when connecting to a ZEO server with authentication
enabled.
""",
    ),
    "zeo-realm": RecipeOption(
      """
Authentication realm to use when authentication with a ZEO server. Defaults
to 'ZEO'.
""",
    ),
    "rel-storage": RecipeOption(
      """
Allows to set a RelStorage instead of a FileStorage.

Contains settings separated by newlines, with these values:

- type: any database type supported (postgresql, oracle, mysql)
- RelStorage specific keys, like `cache-servers` and `poll-interval`
- all other keys are passed on to the database-specific RelStorage adapter.

Example::

  rel-storage =
    type oracle
    dsn (DESCRIPTION=(ADDRESS=(HOST=s01))(CONNECT_DATA=(SERVICE_NAME=d01)))
    user tarek
    password secret
""",
    ),
    "event-log": RecipeOption(
      """
The filename of the event log. Defaults to ${buildout:directory}/var/log/${partname}.log
Setting this value to 'disable' will make the <eventlog> section to be omitted,
disabling logging events by default to a .log file.
""",
    ),
    "event-log-level": RecipeOption(
      """
Set the level of the console output for the event log. Level may be any of
CRITICAL, ERROR, WARN, INFO, DEBUG, or ALL. Defaults to INFO.
""",
    ),
    "event-log-max-size": RecipeOption(
      """
Maximum size of event log file. Enables log rotation.
Used for ZServer only, not WSGI.
""",
    ),
    "event-log-old-files": RecipeOption(
      """
Number of previous log files to retain when log rotation is enabled.
Defaults to 1. Used for ZServer only, not WSGI.
""",
    ),
    "event-log-custom": RecipeOption(
      """
  A custom section for the eventlog, to be able to use another
  event logger than `logfile`. Used for ZServer only, not WSGI.
""",
    ),
    "mailinglogger": RecipeOption(
      """
A mailinglogger section added into the event log.
Used for ZServer only, not WSGI. Example snippet::

  <mailing-logger>
    level error
    flood-level 10
    smtp-server smtp.mydomain.com
    from logger@mydomain.com
    to errors@mydomain.com
    subject [My domain error] [%(hostname)s] %(line)s
  </mailing-logger>

You will need to add `mailinglogger` to your buildout's egg section to make this work.
""",
    ),
    "access-log": RecipeOption(
      """
The filename for the Z2 access log. Defaults to var/log/${partname}-Z2.log
(var/log/${partname}-access.log) for WSGI).
You can disable access logging by setting this value to 'disable'.
For ZServer this will omit the `<logger access>` section in `zope.conf`.
For WSGI, the logging handler will be a `NullHandler <https://docs.python.org/3/library/logging.handlers.html#nullhandler>`_.
"""
    ),
    "z2-log": RecipeOption(
      """
The filename for the Z2 access log. Defaults to var/log/${partname}-Z2.log
(var/log/${partname}-access.log) for WSGI).
You can disable access logging by setting this value to 'disable'.
For ZServer this will omit the `<logger access>` section in `zope.conf`.
For WSGI, the logging handler will be a `NullHandler <https://docs.python.org/3/library/logging.handlers.html#nullhandler>`_.
"""
    ),
    "access-log-level": RecipeOption(
      """
Set the log level for the access log. Level may be any of CRITICAL, ERROR,
WARN, INFO, DEBUG, or ALL. Defaults to WARN (INFO for WSGI).
""",
    ),
    "z2-log-level": RecipeOption(
      """
Set the log level for the access log. Level may be any of CRITICAL, ERROR,
WARN, INFO, DEBUG, or ALL. Defaults to WARN (INFO for WSGI).
""",
    ),
    "access-log-max-size": RecipeOption(
      """
  Maximum size of access log file. Enables log rotation.
  Used for ZServer only, not WSGI.
""",
    ),
    "access-log-old-files": RecipeOption(
      """
  Number of previous log files to retain when log rotation is enabled.
  Defaults to 1. Used for ZServer only, not WSGI.
""",
    ),
    "access-log-custom": RecipeOption(
      """
  Like `event-log-custom`, a custom section for the access logger, to be able
  to use another event logger than `logfile`. Used for ZServer only, not WSGI.
""",
    ),
    "sentry_dsn": RecipeOption(
      """
  Provide a Sentry DSN here to enable basic Sentry logging documented
  in `<https://docs.sentry.io/platforms/python/logging/>`_. You will need to add the
  Python Sentry SDK, either by adding it to your eggs section directly or by adding
  `plone.recipe.zope2instance[sentry]`.
  Available for WSGI only.
""",
    ),
    "sentry_level": RecipeOption(
      """
Set the logging level for Sentry breadcrumbs.
Available for WSGI only.
""",
    ),
    "sentry_event_level": RecipeOption(
      """
Set the logging level for Sentry events.
Available for WSGI only.
""",
    ),
    "sentry_ignore": RecipeOption(
      """
Set the (space separated list of) logger names that are ignored by Sentry.
Available for WSGI only.
""",
    ),
    "sentry_max_value_length": RecipeOption(
      """
Set the maximum size of traceback messages sent to Sentry. If your tracebacks
get truncated, increase this above the sentry-sdk default of 1024.
Available for WSGI only.
""",
    ),
    "access-log-handler": RecipeOption(
      """
  The (dotted) name of an importable Python logging handler like
  `logging.handlers.RotatingFileHandler`.

  Default: `FileHandler`
""",
    ),
    "access-log-args": RecipeOption(
      """
  A python tuple which usually refers to the logging filename and opening mode
  of the file like `("access.log", "a")`.  Note that you a Python tuple with
  only one element (e.g. only the filename) must have a trailing comma like
  `("access.log", )` The `access-log-args` is used to specify the positional
  parameters for the logging handler configured through `access-log-handler`.

  Default: `(r"access.log", "a")`
""",
    ),
    "access-log-kwargs": RecipeOption(
      """
  A python dictionary used for passing keyword argument for the logging handler
  configured through `access-log-handler` e.g.  `{"when": "h", "interval": 1}`.

  Default: `{}`
""",
    ),
    "event-log-handler": RecipeOption(
      """Same as `access-log-handler` but for the configuration of the event log of Plone.
""",
    ),
    "event-log-args": RecipeOption(
      """Same as `access-log-args` but for the configuration of the event log of Plone.
""",
    ),
    "event-log-kwargs": RecipeOption(
      """Same as `access-log-kwargs` but for the configuration of the event log of Plone.
""",
    ),
    "products": RecipeOption(
      """
A list of paths where Zope 2 products are installed. The first path takes
precedence in case the same product is found in more than one directory.
Zope 2 products are deprecated and won't work any longer in a future version
of Zope/Plone.
""",
    ),
    "extra-paths": RecipeOption(
      """
A list of paths where additional Python packages are installed. The paths
are searched in the given order after all egg and products paths.
""",
    ),
    "site-zcml": RecipeOption(
      """
If you want a custom `site.zcml` file, put its content here. If this option
is used the `zcml` and `zcml-additional` options are ignored.
""",
    ),
    "zcml-additional": RecipeOption(
      """
Extra ZCML statements that should be included in the generated `site.zcml`
file.
""",
    ),
    "zeo-client-cache-size": RecipeOption(
      """
Set the size of the ZEO client cache. Defaults to '128MB'. The ZEO cache is
a disk based cache shared between application threads. It is stored either in
temporary files or, in case you activate persistent cache files with the
option `client` (see below), in the folder designated by the `zeo-var`
option.
""",
    ),
    "zeo-client-client": RecipeOption(
      """
Set the persistent cache name that is used to construct the cache
filenames. This enables the ZEO cache to persist across application restarts.
Persistent cache files are disabled by default.
""",
    ),
    "zeo-client-blob-cache-size": RecipeOption(
      """
Set the maximum size of the ZEO blob cache, in bytes.  If not set, then
the cache size isn't checked and the blob directory will grow without bound.
""",
    ),
    "zeo-client-blob-cache-size-check": RecipeOption(
      """
Set the ZEO check size as percent of `zeo-client-blob-cache-size` (for
example, `10` for 10%). The ZEO cache size will be checked when this many
bytes have been loaded into the cache. Defaults to 10% of the blob cache
size. This option is ignored if `shared-blob` is enabled.
""",
    ),
    "zeo-client-drop-cache-rather-verify": RecipeOption(
      """
Indicates that the cache should be dropped rather than verified when
the verification optimization is not available (e.g. when the ZEO server
restarted). Defaults to 'False'.
""",
    ),
    "zeo-storage": RecipeOption(
      """
Set the storage number of the ZEO storage. Defaults to '1'.
""",
    ),
    "zeo-var": RecipeOption(
      """
Used in the ZEO storage snippets to configure the ZEO var folder, which
  is used to store persistent ZEO client cache files. Defaults to the system
  temporary folder.
""",
    ),
    "wsgi-ini-template": RecipeOption(
      """
By default `plone.recipe.zope2instances` uses a hard-coded template for the
generated WSGI configuration in `parts/<partname>/etc/wsgi.ini`. The template
is defined as `wsgi_ini_template` variable within the `recipe.py
<https://github.com/plone/plone.recipe.zope2instance/blob/master/src/plone/recipe/zope2instance/recipe.py>`_
file.

You can override the template with a custom template file using this option.

Example::

    wsgi-ini-template = /path/to/wsgi_template.ini

The available variables for variable substition can be found within the existing template (see above).
""",
    ),
    "asyncore-use-poll": RecipeOption(
      """
By default `false`. If you want the `waitress.asyncore.loop` flag to use poll()
instead of the default select() set to `true`.
""",
    ),
    "before-storage": RecipeOption(
      """
Wraps the base storage in a "before storage" which sets it in
read-only mode from the time given (or "now" for the current time).

This option is normally used together with demo-storage for a
normally running site in order for changes to be made to the
database.
""",
    ),
    "client-home": RecipeOption(
      """
Sets the clienthome for the generated instance.
Defaults to ${buildout:directory}/var/<name of the section>.
""",
    ),
    "clear-untrusted-proxy-headers": RecipeOption(
      """
This tells Waitress to remove any untrusted proxy headers
("Forwarded", "X-Forwarded-For", "X-Forwarded-By",
"X-Forwarded-Host", "X-Forwarded-Port", "X-Forwarded-Proto").
The default in waitress 1 is false, but waitress 2 changes this to true.
We explicitly default to false.
When you set it to true, you may need to set other ``wsgi.ini`` options like
``trusted_proxy_headers`` and ``trusted_proxy``.
Setting those is not supported by the recipe yet.
Used for WSGI only, not ZServer.
""",
    ),
    "default-zpublisher-encoding": RecipeOption(
      """
This controls what character set is used to encode unicode data that reaches
ZPublisher without any other specified encoding. This defaults to 'utf-8'.
Plone requires this to be set to `utf-8`.
""",
    ),
    "demo-storage": RecipeOption(
      """
If 'on' it enables the demo storage. By default, this is a
memory-based storage option; changes are not persisted (see the
demo-file-storage option to use a persistent storage for changes
made during the demonstration).

To use with a base storage option configured with a blob-storage,
you must set a demo-blob-storage.
""",
    ),
    "demo-file-storage": RecipeOption(
      """
If provided, the filename where the ZODB data file for changes
committed during a demonstration will be stored.
""",
    ),
    "demo-blob-storage": RecipeOption(
      """
If provided, the name of the directory where demonstration ZODB blob
data will be stored.

This storage may be connected to a demonstration file storage, or
used with the default memory-based demo storage (in this case you
might want to use a temporary directory).
""",
    ),
    "storage-wrapper": RecipeOption(
      """
Template for arbitrary configuration to be wrapped around the main storage.
%s will be replaced with the existing storage configuration.
""",
    ),
    "effective-user": RecipeOption(
      """
The name of the effective user for the Zope process. Defaults to not setting
an effective user.
""",
    ),
    "enable-product-installation": RecipeOption(
      """
Enable the persistent product registry by setting this to ``on``. By default
the registry is turned ``off``. Enabling the registry is deprecated.
""",
    ),
    "ftp-address": RecipeOption(
      """
Give a port for the FTP server. This enables the FTP server.
Used for ZServer only, not WSGI.
""",
    ),
    "http-force-connection-close": RecipeOption(
      """
Set to `on` to enforce Zope to set ``Connection: close header``.
This is useful if for example a 304 leaves the connection open with
Varnish in front and Varnish tries to reuse the connection.
""",
    ),
    "http-fast-listen": RecipeOption(
      """
Set to `off` to defer opening of the HTTP socket until the end of the Zope
startup phase. Defaults to on.
""",
    ),
    "icp-address": RecipeOption(
      """
Give a port for the ICP server. This enables the ICP server.
Used for ZServer only, not WSGI.
""",
    ),
    "import-directory": RecipeOption(
      """
Used to configure the import directory for instance.
Defaults to `<client-home>/import`.
""",
    ),
    "port-base": RecipeOption(
      """
Offset applied to the port numbers used for ZServer configurations. For
example, if the http-server port is 8080 and the port-base is 1000, the HTTP
server will listen on port 9080. This makes it easy to change the complete
set of ports used by a Zope server process. Zope defaults to 0.
""",
    ),
    "python-check-interval": RecipeOption(
      """
An integer telling the Python interpreter to check for asynchronous events
every number of instructions. This affects how often thread switches occur.
Defaults to 1000.
""",
    ),
    "relative-paths": RecipeOption(
      """
Set this to `true` to make the generated scripts use relative
paths. You can also enable this in the `[buildout]` section.
""",
    ),
    "scripts": RecipeOption(
      """
Add this parameter with no arguments to suppress script generation.
Otherwise (i.e. without this parameter), scripts for packages added
to the `eggs` parameter will be generated. You may also configure
per package. E.g.::

  [instance]
  recipe = plone.recipe.zope2instance
  eggs =
    Plone
    mr.migrator
    my.package
  scripts = my_package_script

In the above example, only `my_package_script` will be generated. Keep in
mind that the egg containing the script (``my.package`` in the example) must
be listed explicitly in the eggs option, even if it is a dependency of an
already listed egg.
""",
    ),
    "template-cache": RecipeOption(
      """
Used to configure the cache for page-template files. Chameleon will write
compile page-templates into this directory and use it as a cache.
See https://chameleon.readthedocs.io/en/latest/configuration.html for more info.
Valid options are off or on or a directory-location.
Defaults to ${buildout:directory}/var/cache (it also confirms to what var is set to).
""",
    ),
    "var": RecipeOption(
      """
Used to configure the base directory for all things going into var.
Defaults to ${buildout:directory}/var.
""",
    ),
    "webdav-address": RecipeOption(
      """
Give a port for the WebDAV server.  This enables the WebDAV server.
Used for ZServer only, not WSGI.
""",
    ),
    "webdav-force-connection-close": RecipeOption(
      """
Valid options are off and on. Defaults to off.
Used for ZServer only, not WSGI.
""",
    ),
    "pipeline": RecipeOption(
      """
The main application pipeline served by the wsgi server.
By default the pipeline is::

  translogger
  egg:Zope#httpexceptions
  zope

The ``translogger`` line in the pipeline will be removed
if ``z2-log`` is set to ``disabled`` or if it is not set
and ``access-log`` is set to ``disabled`` (case insensitive).
Used for WSGI only, not ZServer.
""",
    ),
    "zlib-storage": RecipeOption(
      """
Adds support for file compression on a file storage database. The
option accepts the values 'active' (compress new records) or
'passive' (do not compress new records). Both options support
already compressed records.

You can use the 'passive' setting while you prepare a number of
connected clients for compressed records.
""",
    ),
    "zodb-cache-size-bytes": RecipeOption(
      """
Set the ZODB cache sizes in bytes. This feature is still experimental.
""",
    ),
    "zodb-temporary-storage": RecipeOption(
      """
If given Zope's default temporary storage definition will be replaced by
the lines of this parameter. If set to "off" or "false", no temporary storage
definition will be created. This prevents startup issues for basic Zope 4
sites as it does not ship with the required packages by default anymore.
""",
    ),
    "zope-conf": RecipeOption(
      """
A relative or absolute path to a `zope.conf` file. If this is given, many of
the options in the recipe will be ignored.
""",
    ),
    "zope-conf-imports": RecipeOption(
      """
You can define custom sections within zope.conf using the ZConfig API.
But, in order for Zope to understand your custom sections, you'll have to
import the python packages that define these custom sections using `%import`
syntax.

Example::

  zope-conf-imports =
    mailinglogger
    eea.graylogger
""",
    ),
    "zope-conf-additional": RecipeOption(
      """
Give additional lines to `zope.conf`. Make sure you indent any lines after
the one with the parameter.

Example::

  zope-conf-additional =
    locale fr_FR
    http-realm Slipknot
""",
    ),
    "zopectl-umask": RecipeOption(
      """
Manually set the umask for the zopectl process.

Example::

  zopectl-umask = 002
""",
    ),
    "http-header-max-length": RecipeOption(
      """
Manually set the maximum size of received HTTP header being processed by Zope.
The request is discarded and considered as a DoS attack if the header size exceeds
this limit. Default: 8192. Used for ZServer only, not WSGI.

Example::

  http-header-max-length = 16384

""",
    ),
  },
)
