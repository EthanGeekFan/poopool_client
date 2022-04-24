import os
import csv


def record_block(block, private_key, public_key, blockid, height):
    """
    Record the block into a file.
    """
    # Build the content of the record.
    content = [height, blockid, block, private_key, public_key]
    file_name = os.path.join(os.getcwd(), 'blocks.csv')
    with open(file_name, 'a+') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(content)
    return file_name


def clean_nul_storage(file_name=os.path.join(os.getcwd(), 'blocks.csv')):
    """
    Clean the record.
    """
    with open(file_name, 'rb') as f:
        data = f.read()
    with open(file_name, 'wb') as f:
        f.write(data.replace(bytes([0]), ''.encode("utf-8")))


def resume():
    """
    Resume from the record.
    """
    clean_nul_storage()
    file_name = os.path.join(os.getcwd(), 'blocks.csv')
    with open(file_name, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        records = list(reader)
        if len(records) < 1:
            # genesis
            return "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e", 0
        index = len(records) - 1
        while len(records[index]) == 0:
            index -= 1
        return records[index][1], int(records[index][0]) + 1
