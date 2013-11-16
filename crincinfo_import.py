from BeautifulSoup import BeautifulSoup
from datetime import timedelta, datetime
from crick_util import mysql_execute, mysql_fetchall

dbg=False

def import_player(data):
    soup = BeautifulSoup(data)

    head=soup.findAll('tr', {'class': 'headlinks'})

    ths = head[0].findAll('th')

    trs=soup.findAll('tr', {'class':'data1'})

    for tr in trs:
        tds=tr.findAll('td')
        print tds

def add_playerresult(vals, team, player):
    allvals = vals + (team, player)
    SQL = """ INSERT IGNORE INTO scorecard
                (runs,mins,balls,fours,sixes,pos,dismissal,odi,team,player)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """ 
    #print allvals
    mysql_execute(SQL, *allvals)

def add_matchresult(vals, team):
    allvals = vals + (team,)
    SQL = """ INSERT IGNORE INTO matchresults
                (score, overs, inns, result, vsteam, ground, at, odi, url,
                team) values (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s)
            """ 
    mysql_execute(SQL, *allvals)

def playerresults_row(tr):
    tds=tr.findAll('td')
    runs = int(tds[0].text.split('*',1)[0])
    if dbg: print "runs", runs
    try:
        mins = int(tds[1].text)
    except ValueError, e:
        mins = 0
    if dbg: print "mins", mins
    balls = int(tds[2].text)
    if dbg: print "balls", balls
    fours = int(tds[3].text)
    if dbg: print "fours", fours
    sixes = int(tds[4].text)
    if dbg: print "sixes", sixes
    pos = int(tds[6].text)
    dismissal = tds[7].text.lower()
    if dbg: print "pos", pos
    odia = tds[13].find('a')
    odi = int(odia.text[6:])
    if dbg: print "odi", odi
    return (runs,mins,balls,fours,sixes,pos,dismissal,odi)


def matches_row(tr):
    tds = tr.findAll('td')
    team1 = tds[0].text
    team2 = tds[1].text
    winner = tds[2].text
    margin = tds[3].text
    ground = tds[4].text
    match_date = datetime.strptime(tds[5].text, "%b %d, %Y").date()
    id = int(tds[6].text.split()[2])
    odi_url = tds[6].find('a')['href']

    return (id, team1, team2, winner, margin, ground, match_date, odi_url)


def matchresults_row(tr):
    tds=tr.findAll('td')
    score = int(tds[0].text.split('/',1)[0])
    overs = int(tds[1].text.split('.',1)[0])
    inns = int(tds[4].text)
    result = tds[5].text
    vsteam = tds[7].find('a').text.lower()
    ground = tds[8].find('a').text.lower()
    at = tds[9].find('b').text
    at = datetime.strptime(at, "%d %b %Y")
    odia = tds[10].find('a')
    odi = int(odia.text[6:])
    url = ""
    for attr,val in odia.attrs:
        if attr=='href':
            url = val
            break
    return (score, overs, inns, result, vsteam, ground, at, odi, url)

def process_matchresults_row(tr, team, player):
    vals = matchresults_row(tr)
    add_matchresult(vals, team)

def process_playerresults_row(tr, team, player):
    vals = playerresults_row(tr)
    add_playerresult(vals, team, player)

def import_matchresults(data, team, player=None):
    import_results (data, team, process_matchresults_row, player)

def import_playerresults(data, team, player):
    import_results (data, team, process_playerresults_row, player)

def import_results(data, team, import_func, player=None):
    soup = BeautifulSoup(data)

    tables=soup.findAll('table', {'class': 'engineTable'})
    # find table with correct caption
    maintable = None
    for table in tables:
        cap=table.find('caption')
        if cap != None and cap.text == 'Innings by innings list':
            maintable=table
            break
    trs = maintable.findAll ('tr', {'class':'data1'})
    cnt = 0
    for tr in trs:
        try:
            import_func(tr,team,player)
            cnt += 1
        except Exception, e:
            print e

    print "processed ", cnt,"/", len(trs)

def import_matches(data):
    soup = BeautifulSoup(data)

    tables=soup.findAll('table', {'class': 'engineTable'})
    # find table with correct caption
    maintable = None
    for table in tables:
        cap=table.find('caption')
        if cap != None and cap.text == 'Match results':
            maintable=table
            break
    trs = maintable.findAll ('tr', {'class':'data1'})
    cnt = 0
    for tr in trs:
        try:
            res = matches_row(tr)
            mysql_execute("INSERT IGNORE INTO odi values(%s,%s,%s,%s,%s,%s,%s,%s)", *res)
            cnt += 1
        except Exception, e:
            print e

def import_match(data):
    soup = BeautifulSoup(data)


def main():
    import sys
    data=open(sys.argv[1], 'rt').read()
    import_matchresults(data, sys.argv[2])
    #data=open('./sachin.html', 'rt').read()
    #import_playerresults(data, 'india', 'sachin tendulkar')
    #data=open('./viv_richards.html', 'rt').read()
    #import_playerresults(data, 'west indies', 'viv richards')
    #data=open('./india.html', 'rt').read()
    #import_matchresults(data, 'india')
    #data=open('./pakistan.html', 'rt').read()
    #import_matchresults(data, 'pakistan')
    #data=open('./australia.html', 'rt').read()
    #import_matchresults(data, 'australia')
#    data=open('./england.html', 'rt').read()
#    import_matchresults(data, 'england')
#    data=open('./west_indies.html', 'rt').read()
#    import_matchresults(data, 'west indies')
#    data=open('./south_africa.html', 'rt').read()
#    import_matchresults(data, 'south africa')
#    data=open('./new_zealand.html', 'rt').read()
#    import_matchresults(data, 'new zealand')
    #data=open('./sri_lanka.html', 'rt').read()
    #import_matchresults(data, 'sri lanka')

if __name__ == "__main__":
    main()
