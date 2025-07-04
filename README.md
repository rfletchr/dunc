# Dunc 
A dumb and dirt-simple 'build tool' for rez.

## Usage


```python
# package.py

name = "test"
version = "0.0.1"

install_requires = ["dunc"] 

build_command = "dunc"

def commands():
    env.PATH.append("{root}/bin")

def install():
    import dunc

    files = dunc.find_files("src/**/*.py")
    dunc.install_files(
        files,
        symlink=True,
    )

```

