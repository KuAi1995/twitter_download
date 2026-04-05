import csv
from datetime import datetime
from utils import stamp2time_csv


class csv_gen():
    def __init__(self, save_path: str, user_name, screen_name, tweet_range) -> None:
        self.f = open(f'{save_path}/{screen_name}-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv', 'w', encoding='utf-8-sig', newline='')
        self.writer = csv.writer(self.f)

        self.writer.writerow([user_name, screen_name])
        self.writer.writerow(['Tweet Range : ' + tweet_range])
        self.writer.writerow(['Save Path : ' + save_path])
        main_par = ['Tweet Date', 'Display Name', 'User Name', 'Tweet URL', 'Media Type', 'Media URL', 'Saved Filename', 'Tweet Content', 'Favorite Count',
                    'Retweet Count', 'Reply Count']
        self.writer.writerow(main_par)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.csv_close()

    def csv_close(self):
        self.f.close()

    def data_input(self, main_par_info: list) -> None:
        main_par_info[0] = stamp2time_csv(main_par_info[0])
        self.writer.writerow(main_par_info)
