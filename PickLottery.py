from collections import Counter
from bs4 import BeautifulSoup
from threading import Timer
from datetime import datetime
import random
import time
import calendar
import yaml
import requests
import warnings
import pandas as DataFrame

warnings.filterwarnings('ignore')

with open('config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
ROUNDING = _cfg['ROUNDING']
LOTTO_URL = _cfg['LOTTO_URL']
EXCEL_URL = _cfg['EXCEL_URL']

def message(msg):
    """디스코드 메세지 전송"""
    now = datetime.now()
    message = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"
    requests.post(DISCORD_WEBHOOK_URL, data={"content": message})
    print(message)

def progress_bar(current: int, total: int, width=50):
    """ 진행 상황 표시 """
    percent = float(current) / float(total)
    bar = "#" * int(percent * width)
    empty = " " * (width - len(bar))
    print("\rProgress: [{0}] {1}/{2} ({3:.0f}%)".format(bar + empty, current, total, percent * 100), end="")

def get_last_round():
    """ 가장 최근 로또 번호 가져오기 """
    html = requests.get(LOTTO_URL).text
    soup = BeautifulSoup(html, 'lxml')
    last_round = int(soup.find('strong', id='lottoDrwNo').text)
    return last_round

def get_win_numbers():
    """ 역대 당첨 번호 가져오기 """
    last_round = get_last_round()
    url = f'{EXCEL_URL}{last_round}'
    df = DataFrame.read_html(url, header=0, encoding='cp949')[1]
    df = df.rename(columns=df.iloc[0])
    df = df.drop(0, axis=0)
    #df = df[['회차','추첨일',1,2,3,4,5,6,'보너스']]
    #df = df.rename(columns={'회차':'round','추첨일':'date',1:'1',2:'2',3:'3',4:'4',5:'5',6:'6','보너스':'bonus'})
    df = df[[1,2,3,4,5,6]]
    df = df.rename(columns={1:'1',2:'2',3:'3',4:'4',5:'5',6:'6'})
    df = df.reset_index(drop=True)
    return df

def fill_random_number(numbers: list):
    """ 무작위 숫자 채우기 """
    random_number = random.randint(1, 45)
    for i in range(len(numbers), 6):
        while random_number in numbers:
            random_number = random.randint(1, 45)
        numbers.append(random_number)
    numbers.sort()

def is_exists(lotto: list, winning_numbers: DataFrame):
    """ 데이터 프레임에서 동일 숫자 배열이 있는지 확인 """
    condition = (
        (winning_numbers['1'] == lotto[0])&
        (winning_numbers['2'] == lotto[1])&
        (winning_numbers['3'] == lotto[2])&
        (winning_numbers['4'] == lotto[3])&
        (winning_numbers['5'] == lotto[4])&
        (winning_numbers['6'] == lotto[5])
    )
    return condition.any()

def generate_lotto_set(**kwargs):
    """ 옵션에 따라 숫자 생성하기 """
    lotto_set = []
    
    ''' 소수 포함 갯수 (추천: 3개) '''
    if kwargs.get("prime_count") is not None:
        count = kwargs.get("prime_count")
        if count == 0:
            exclude_numbers = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43]
            while(len(lotto_set) != 6):
                fill_random_number(lotto_set)
                lotto_set = list(set(lotto_set) - set(exclude_numbers))
        elif 1 <= count and count <= 6:
            prime_numbers = random.sample([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43], count)
            lotto_set.extend(prime_numbers)
            fill_random_number(lotto_set)
    
    ''' 총 합이 특정 숫자 이하 '''
    if kwargs.get("less_then") is not None:
        total = kwargs.get("less_then")
        min = sum([1, 2, 3, 4, 5, 6])
        if total < min:
            total = min + 10
        while True:
            lotto_set = random.sample(range(1, 46), 6)
            if sum(lotto_set) <= total:
                break
    
    ''' 총 합이 특정 숫자 이상 '''
    if kwargs.get("greater_then") is not None:
        total = kwargs.get("greater_then")
        max = sum([40, 41, 42, 43, 44, 45])
        if total > max:
            total = max - 10
        while True:
            lotto_set = random.sample(range(1, 46), 6)
            if sum(lotto_set) >= total:
                break
            
    ''' 첫 자리 수 합이 특정 값 '''
    # TODO: 예외처리 추가 (0 - 24)
    if kwargs.get("first_sum") is not None:
        total = kwargs.get("first_sum")
        while True:
            lotto_set = random.sample(range(1, 46), 6)
            first_numbers = [num // 10 % 10 for num in lotto_set]
            if sum(first_numbers) == total:
                break
        
    ''' 끝 자리 수 합이 특정 값 '''
    # TODO: 예외처리 추가 (2 - 52)
    if kwargs.get("last_sum") is not None:
        total = kwargs.get("last_sum")
        while True:
            lotto_set = random.sample(range(1, 46), 6)
            last_numbers = [num % 10 for num in lotto_set]
            if sum(last_numbers) == total:
                break
            
    ''' 홀이나 짝으로 구성 '''
    # TODO: 예외처리 추가
    if kwargs.get("parity") is not None:
        if str(kwargs.get("parity")).lower() == "odd":
            parity = 1
        elif str(kwargs.get("parity")).lower() == "even":
            parity = 0
        else:
            return []
        while True:
            lotto_set = random.sample(range(1, 46), 6)
            if all([num % 2 == parity for num in lotto_set]):
                break

    ''' 포함 할 숫자들 '''
    # TODO: 예외처리 추가 (1 - 45)
    if kwargs.get("include_numbers") is not None:
        include_numbers = kwargs.get("include_numbers")
        lotto_set.extend(include_numbers)
        fill_random_number(lotto_set)

    ''' 제외 할 숫자들 '''
    # TODO: 예외처리 추가 (1 - 45)
    if kwargs.get("exclude_numbers") is not None:
        exclude_numbers = kwargs.get("exclude_numbers")
        while(len(lotto_set) != 6):
            fill_random_number(lotto_set)
            lotto_set = list(set(lotto_set) - set(exclude_numbers))
    
    ### 얼만큼 연달아 나오는걸 허용하는지가 아닌가?
    ''' 연속 숫자 수량 '''
    # TODO: 예외처리 추가 (1 - 6)
    if kwargs.get("continuity_count") is not None:
        count = kwargs.get("continuity_count")
        start_number = random.randint(1, 45 - count)
        for i in range(start_number, start_number + count):
            lotto_set.append(i)
        fill_random_number(lotto_set)
    
    ''' 기본 '''
    if not kwargs:
        fill_random_number(lotto_set)

    return sorted(lotto_set)

def get_lotto_set(winning_numbers: DataFrame):
    """ 역대 당첨 번호를 제외해서 번호 생성 """
    # TODO: 옵션 기능 사용 안함
    lotto_set = generate_lotto_set()
    while (is_exists(lotto_set, winning_numbers)):
        lotto_set = generate_lotto_set()
    return lotto_set

def execute_weekly():
    """ 실행 즉시 또는 매주 오후 다섯시에 숫자 생성 및 통보 """
    
    ''' 로또 번호 만들기 '''
    try:
        lotto_counts = Counter()
        winning_numbers = get_win_numbers()
        for i in range(ROUNDING): # 실행 횟수만큼 생성하여 상위 6개 숫자 추천
            # lotto = random.sample(range(1, 46), 6)
            lotto = get_lotto_set(winning_numbers)
            lotto_counts.update(lotto)
            progress_bar(i + 1, ROUNDING)
        list = lotto_counts.most_common(6)
        nums = [item[0] for item in list]
        print('\r')
        message("Recommendation : %s" % sorted(nums))
    except KeyboardInterrupt:
        message("Ctrl+C detected. Exiting...")
        exit(0)
    
    ''' 다음 실행 예약 '''
    current_time = datetime.now()
    last_day = calendar.monthrange(current_time.year, current_time.month)[1]
    if current_time.month == 12 and current_time.day == last_day: # 다음해로 넘기기
        next_time = current_time.replace(year=current_time.year+1, month=1, day=current_time.day+7, hour=17, minute=0, second=0)
    elif current_time.day == last_day: # 다음달로 넘기기
        next_time = current_time.replace(month=current_time.month+1, day=current_time.day+7, hour=17, minute=0, second=0)
    else: # 다음주 계산하기
        next_time = current_time.replace(day=current_time.day+7, hour=17, minute=0, second=0)
    diff_time = next_time - current_time
    secs = diff_time.seconds

    message("Waiting for next days ({}) ... ".format(next_time.strftime('%Y-%m-%d %H:%M')))
    timer = Timer(secs, execute_weekly)
    timer.setDaemon(True)
    timer.start()

if __name__ == '__main__':
    message("Start generating lottery !!!")
    execute_weekly()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        message("Ctrl+C detected. Exiting...")
        exit(0)
