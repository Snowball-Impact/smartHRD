from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time

# 크롬 옵션 설정
options = Options()
options.add_argument("--headless")  # 브라우저 창을 띄우지 않음
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=options)
url = "https://www.ksqa.or.kr/?pid=HP010201"
driver.get(url)
# time.sleep(2)  # 페이지 로딩 대기

soup = BeautifulSoup(driver.page_source, "html.parser")

rows = []
for tr in soup.select("table.table_list tr"):
    tds = tr.select("td")
    if len(tds) < 5:
        continue
    link_tag = tds[2].select_one("a")
    title = link_tag.get_text(strip=True) if link_tag else ""
    href = urljoin(url, link_tag["href"]) if link_tag else ""
    rows.append({
        "제목": title,
        "URL": href,
        "등록일": tds[4].get_text(strip=True)
    })

df = pd.DataFrame(rows)
driver.quit()

# URL에서 pid 추출하여 csv 로 저장
# directory = r"C:\Users\com\Desktop\고용24API\데이터셋\직업능력심사평가원"
pid = parse_qs(urlparse(url).query).get("pid", [""])[0]
filename_map = {
    "HP010101": "심사평가원_공지사항",
    "HP010201": "심사평가원_심사평가공고",
}
base_filename = filename_map.get(pid, f"심사평가원_{pid}")
csv_filename = f"{base_filename}.csv"
# date_suffix = datetime.now().strftime("%y%m%d")
# csv_filename = f"{directory}\\{base_filename}_{date_suffix}.csv"

df.to_csv(csv_filename, index=False, encoding="utf-8-sig")

# print(df)
# print(f"CSV 저장 완료: {csv_filename}")
