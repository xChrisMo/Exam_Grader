import os

def main():
    file_path = os.path.join('temp', 'simple_test.txt')
    print(f"Testing file: {file_path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"File exists: {os.path.exists(file_path)}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"File content:\n{content}")
    except Exception as e:
        print(f"Error reading file: {str(e)}")

if __name__ == '__main__':
    main() 