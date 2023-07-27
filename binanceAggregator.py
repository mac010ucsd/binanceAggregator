import requests
import os
import shutil

# parameters for coin ohlc data
START_YEAR = 2023
START_MONTH = 1
DURATION = 2    # time period (months)
COIN = "BNBUSDT"

# csv folder name (Don't need to change)
CSV_FOLDER = "csvs"

# temp filename for zip file to be saved as (don't need to change)
filename = "temp.zip"

# from https://stackoverflow.com/a/9419208
def download_url(url, save_path, chunk_size=128):
    r = requests.get(url, stream=True)
    with open(save_path, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)


#url = ' https://data.binance.vision/data/spot/monthly/klines/BNBUSDT/1m/BNBUSDT-1m-2019-01.zip'


#download_url(url, os.path.join(CSV_FOLDER, filename))
#shutil.unpack_archive(os.path.join(CSV_FOLDER, filename), CSV_FOLDER)

def generate_url(symbol, year, month, interval="1h"):
    return f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{year}-{month:02d}.zip"

'''
def extract_dir(CSV_FOLDER, outdir):
    zips = [i for i in os.listdir(CSV_FOLDER) if os.path.isfile(os.path.join(CSV_FOLDER,i))]
    for i in zips:
        shutil.unpack_archive(os.path.join(CSV_FOLDER, i), outdir)
'''

it = START_YEAR * 12 + START_MONTH - 1


if not os.path.isdir("logs"):
    os.mkdir("logs")

if not os.path.isdir(CSV_FOLDER):
    os.mkdir(CSV_FOLDER)
else:
    for i in os.listdir(CSV_FOLDER):
        os.rename(os.path.join(CSV_FOLDER, i), os.path.join("logs",i))

for i in range(DURATION):
    cur_year = (it+i)//12
    cur_month = (it+i)%12+1
    cur_url = generate_url(COIN, cur_year, cur_month)
    print(cur_url)
    download_url(cur_url, os.path.join(CSV_FOLDER, filename))
    shutil.unpack_archive(os.path.join(CSV_FOLDER, filename), CSV_FOLDER)

os.remove(os.path.join(CSV_FOLDER,filename))

csv_list = [i for i in os.listdir(CSV_FOLDER) if os.path.isfile(os.path.join(CSV_FOLDER,i))]
with open(f"output_{COIN}_{START_YEAR}-{START_MONTH}_{DURATION}months.csv" ,"w") as out:
    for i in csv_list[::-1]:
        with open(os.path.join(CSV_FOLDER, i), "r") as r: 
            out.write(r.read())