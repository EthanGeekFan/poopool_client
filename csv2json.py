import csv
import json
import record
import main


def make_json(csv_file_path, json_file_path):
    record.clean_nul_storage(csv_file_path)
    data = []
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            entry = {
                'block': row['Object'],
                'privateKey': row['Private Key'],
                'publicKey': row['Public Key'],
                'transaction': main.canonicalize({
                    "height": row['Height'],
                    "outputs": [
                        {
                            "pubkey": row['Public Key'],
                            "value": 5e13,
                        }
                    ],
                    "type": "transaction",
                }),
                'height': int(row['Height']),
                'blockid': row['Block ID'],
            }
            data.append(entry)

    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)


if __name__ == '__main__':
    csv_file_path = './blocks.csv'
    json_file_path = './blocks.json'
    make_json(csv_file_path, json_file_path)

