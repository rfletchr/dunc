name = "dunc"


version = "1.0.3"


requires = ["python-3"]

build_command = "{root}/bin/dunc"


def commands():
    env.PATH.append("{root}/bin")
    env.PYTHONPATH.append("{root}/src")


def install():
    import dunc

    dunc.install_files(dunc.find_files("src/**/*.py", recursive=True))
    dunc.install_files(dunc.find_files("bin/*"), executable=True)
