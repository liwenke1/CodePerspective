from feature import FileParser


def main():
    parser = FileParser()
    print(parser.parse('resources/hello.java'))

if __name__ == '__main__':
    main()