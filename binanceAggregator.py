import requests
import os
import shutil

# change below
COINS = ["BTCUSD_PERP", "BNBUSD_PERP", "ETHUSD_PERP"]
START_YEAR = 2023   # start year any
START_MONTH = 1     # start month 1-12
DURATION = 6        # duration (total data period) in MONTHS
SMA_PERIOD = 24*7   # sma period in HOURS

# csv folder name (Don't need to change)
CSV_FOLDER = "csvs"
LOG_FOLDER = "logs"

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
    return f"https://data.binance.vision/data/futures/cm/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{year}-{month:02d}.zip"

'''
def extract_dir(CSV_FOLDER, outdir):
    zips = [i for i in os.listdir(CSV_FOLDER) if os.path.isfile(os.path.join(CSV_FOLDER,i))]
    for i in zips:
        shutil.unpack_archive(os.path.join(CSV_FOLDER, i), outdir)
'''

def calc_sma(csv_data, periods=24*7):
    '''
    Calculate the SMA over a certain number of total periods (in hours)
    '''
    # maybe pandas will be faster. but did not test yet
    # open time, open, high, low, close, vol
    rows = csv_data.strip().split("\n")
    for i in range(len(rows)):
        rows[i] = rows[i].split(",")
        # time increases as we go down. 
        # note that we need to be at <periods> before we can start getting sma
    cur_sum = 0
    for i in range(0, periods):
        cur_sum += float(rows[i][4])
    rows[periods-1].append(f"{cur_sum/periods}")
    for i in range(periods, len(rows)):
        # we can simply take the sma of the prev, subtract the first / period
        # then add current / period.
        cur_close = float(rows[i][4])
        prev_sma = float(rows[i-1][-1])
        cur_sma = prev_sma - float(rows[i-periods][4])/periods + cur_close/periods
        rows[i].append(str(cur_sma))
        # we will add another cell on end for the 
        # we can re-join the old ones into a string
        rows[i-periods] = ",".join(rows[i-periods])
    for i in range(len(rows)-periods, len(rows)):
        rows[i] = ",".join(rows[i])
    
    return "\n".join(rows)

    # join it all together.


def get_sma(coin, start_year, start_month, duration_months, sma_period):

    it = start_year * 12 + start_month - 1

    if not os.path.isdir(LOG_FOLDER):
        os.mkdir(LOG_FOLDER)

    if not os.path.isdir(CSV_FOLDER):
        os.mkdir(CSV_FOLDER)
    else:
        for i in os.listdir(CSV_FOLDER):
            os.rename(os.path.join(CSV_FOLDER, i), os.path.join(LOG_FOLDER,i))

    for i in range(duration_months):
        cur_year = (it+i)//12
        cur_month = (it+i)%12+1
        cur_url = generate_url(coin, cur_year, cur_month)
        print(cur_url)
        download_url(cur_url, os.path.join(CSV_FOLDER, filename))
        shutil.unpack_archive(os.path.join(CSV_FOLDER, filename), CSV_FOLDER)

    os.remove(os.path.join(CSV_FOLDER,filename))

    csv_list = [i for i in os.listdir(CSV_FOLDER) if os.path.isfile(os.path.join(CSV_FOLDER,i))]
    with open(f"output_{coin}_{start_year}-{start_month}_{duration_months}months.csv" ,"w") as out:
        for i in csv_list[::-1]:
            with open(os.path.join(CSV_FOLDER, i), "r") as r: 
                for j in r.readlines()[1:]:
                    out.write(j)

    # re-load data back in. this is not really necessary and could be done
    # without even writing this first file to disk.
    with open(f"output_{coin}_{start_year}-{start_month}_{duration_months}months.csv" ,"r") as r:
        o = calc_sma(r.read(), periods=sma_period)

    # calc smaa
    with open(f"output_{coin}_{start_year}-{start_month}_{duration_months}months_sma.csv" ,"w") as out:
        out.write(o)

    # remove non smaa file
    # again, this file was only created and written on disk just for
    # debugging purposes
    os.remove(f"output_{coin}_{start_year}-{start_month}_{duration_months}months.csv")

    # cleanup, move every csv into logs
    # just debugging stuff mainly
    for i in os.listdir(CSV_FOLDER):
        os.rename(os.path.join(CSV_FOLDER, i), os.path.join("logs",i))

for i in COINS:
    get_sma(i, 2023, 1, 6, 24*7)