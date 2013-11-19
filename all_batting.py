#!/usr/bin/env python

"""
http://stats.espncricinfo.com/ci/engine/stats/index.html?class=2;orderby=start;orderbyad=reverse;page=1;result=1;result=2;result=3;result=5;template=results;type=batting;view=innings


Matches for a year
http://stats.espncricinfo.com/india/engine/records/team/match_results.html?class=2;id=2010;type=year

"""
import requests
import os
import crincinfo_import
from crick_util import mysql_execute, mysql_fetchall
from BeautifulSoup import BeautifulSoup
import difflib
import itertools
import traceback


DIRNAME = os.path.dirname(os.path.abspath(__file__))


def import_year(year, force=False):
    """
    import a years worth of odi data
    into the database
    """

    # check if file is already downloaded

    datadir = DIRNAME + "/data"
    yearfile = "{}/matches.{}".format(datadir, year)
    yearurl = ("http://stats.espncricinfo.com/india/engine/records/"
               "team/match_results.html?class=2;id={};type=year".format(year))

    print yearurl

    if os.path.exists(yearfile):
        data = open(yearfile).read()
    else:
        data = requests.get(yearurl).text
        with open(yearfile, "wt") as fl:
            fl.write(data)

    print "Got {} bytes".format(len(data))
    # data is what we need
    crincinfo_import.import_matches(data)


def filt(trs):
    trsout = []
    for tr in trs:
        if tr.name == 'tr':
            try:
                if tr['class'] in ["inningsRow", "inningsComms"]:
                    trsout.append(tr)
            except KeyError:
                pass
    return trsout


class obj(object):
    def __repr__(self):
        return self.__dict__.__repr__()


def getint(val):
    try:
        return int(val)
    except ValueError:
        return 0
import re
RE_CB = re.compile("c\s+(.*)\s+b\s+(.*)$")
RE_STB = re.compile("st\s+(.*)\s+b\s+(.*)$")
RE_B = re.compile("b\s+(.*)$")
RE_RO = re.compile("run out \((\w+)(/s+)*\)")
# >10-220 (Nasir Hossain, 48.5 ov)<
# >2-35 (Tendulkar)<
#RE_FOW = re.compile("(\d+)-(\d+)\*{0,1}\s*(.*?),\s*(\S+)")
RE_FOW = re.compile("(\d+)-(\d+)\*{0,1}\s*\((.*)")
# runout ==>  run out (Khan/Karthik)
# lbw b bhubhu


def resolve_name(pname, names):
    pname = pname.strip()
    ns = difflib.get_close_matches(pname, names, n=1)

    if len(ns) > 0:
        return ns[0]
    else:
        ns = difflib.get_close_matches(pname, names, n=1, cutoff=0.4)
        if len(ns) > 0:
            print "Trying approx match {} ==> {}  {}".format(pname, ns[0], names)
            return ns[0]
        else:
            return pname


def wicket(bat, wtype, bowl=None, assist=None):
    bat.out_type = wtype
    bat.out_by = bowl
    bat.out_assist = assist


def resolve_match(bat1, bowl1, bat2, bowl2, summ1, summ2):
    player = {}

    for bn in itertools.chain(bat1, bat2, bowl1, bowl2):
        player[bn.player] = bn.playerid

    names = player.keys()

    for bat in itertools.chain(bat1, bat2):
        if bat.dismissal.startswith("run out"):
            dm = bat.dismissal[len("run out"):]
            wicket(bat, "runout", assist=resolve_name(dm.partition("/")[0], names))
            continue

        if "not out" in bat.dismissal:
            wicket(bat, "notout")
            continue

        if bat.dismissal.startswith("lbw"):
            bowler = bat.dismissal[5:]
            wicket(bat, "lbw", resolve_name(bowler, names))
            continue

        rm = RE_CB.match(bat.dismissal)
        if rm is not None:
            grp = rm.groups()
            # if caught and bowled grp[0] = "&"
            bowled = grp[1]
            caught = grp[0]
            if caught == "&" or caught == "&amp;":
                caught = bowled
            wicket(bat, "caught", resolve_name(bowled, names), resolve_name(caught, names))
            continue
        else:
            rm = RE_B.match(bat.dismissal)
            if rm is not None:
                grp = rm.groups()
                wicket(bat, "bowled", resolve_name(grp[0], names))
                continue
            else:
                rm = RE_STB.match(bat.dismissal)
                if rm is not None:
                    grp = rm.groups()
                    wicket(bat, "stumped", resolve_name(grp[1], names), resolve_name(grp[0], names))
                    continue

        # if none matched then just use it
        dm = bat.dismissal.split()[0]
        wicket(bat, dm)

    return names


def update_summary(odi, tbl, teamNo):
        trs = filt(tbl[0].findAll('tr'))
        summary = trs[-1]
        runs = summary.find('td', {'class': 'battingRuns'}).text
        wick = summary.find('td', {'class': 'battingDismissal'})
        spl = wick.text[1:-1].split(';')
        wck = spl[0].strip().split()[0]
        if wck == "all":
            wck = "10"
        ovr = spl[1].strip().split()[0]

        SQL = "update odi set team{}_runs=%s, team{}_wickets=%s, team{}_overs=%s where id=%s".format(teamNo,
                                     teamNo, teamNo)
        mysql_execute(SQL, runs, wck, ovr, odi)

        # runs, wickets, overs
        return (runs, wck, ovr)


def fetch_odi(year, odi_ids=None, force=False, toyear=None):
    toyear = toyear or year
    sql = """select id, odi_url, winner
             from odi where match_date>='{}-01-01' and
             match_date <= '{}-12-31'""".format(year, toyear)
    if odi_ids is not None:
        sql += " and id in ({})".format(str(odi_ids)[1:-1])
    odis = mysql_fetchall(sql)
    datadir = DIRNAME + "/data"

    for idx, odi in enumerate(odis):
        if not force:
            scores = mysql_fetchall("select inns, count(*) as cnt from score where odi=%s group by inns", odi.id)
            if len(scores) > 0:
                slist = [r.cnt for r in scores if r.cnt >= 2]
                if len(slist) == 2:
                    print "{} records already in db for {}".format(slist, odi)
                    continue
                elif odi.winner.lower() == 'no result':
                    continue

        try:
            matchfile = "{}/matche.{}".format(datadir, odi.id)
            match_url = "http://www.espncricinfo.com{}".format(odi.odi_url)
            if os.path.exists(matchfile):
                data = open(matchfile).read()
            else:
                print match_url
                data = requests.get(match_url).text
                with open(matchfile, "wt") as fl:
                    try:
                        fl.write(data)
                    except UnicodeEncodeError:
                        fl.write(data.encode('utf-8'))

            soup = BeautifulSoup(data)
            tbl = soup.findAll('table', {'id': 'inningsBat1'})
            th = tbl[0].find('tr', {'class': 'inningsHead'})
            summ1 = update_summary(odi.id, tbl, 1)
            tdd = th.findAll('td')[1]
            team1 = tdd.text.partition('innings')[0].strip()
            bat1 = get_innings(tbl)
            tbl = soup.findAll('table', {'id': 'inningsBowl1'})
            bowl1 = get_innings(tbl)
            tbl = soup.findAll('table', {'id': 'inningsBat2'})
            summ2 = update_summary(odi.id, tbl, 2)
            th = tbl[0].find('tr', {'class': 'inningsHead'})
            tdd = th.findAll('td')[1]
            team2 = tdd.text.partition('innings')[0].strip()
            bat2 = get_innings(tbl)
            tbl = soup.findAll('table', {'id': 'inningsBowl2'})
            bowl2 = get_innings(tbl)
            names = resolve_match(bat1, bowl1, bat2, bowl2, summ1, summ2)
            # write results to database
            # print bat1, bat2

            tbls = soup.findAll('table', {'class': 'inningsTable'})
            fow = {}
            for _tbl in tbls:
                _trs = _tbl.findAll('tr')
                if len(_trs) > 1:
                    continue
                if _trs[0].text.lower().startswith("fall of wickets"):
                    for ll in _trs[0].text[len("Fall of wickets"):].split('),'):
                        mm = RE_FOW.match(ll)
                        if "retired" in ll and mm:
                            grp = mm.groups()
                            name, _, ov = grp[2].partition(",")
                            fow[resolve_name(name, names)] = (int(grp[0]), int(grp[1]), 5)
                            continue
                        if "not out" in ll:
                            continue
                        if mm:
                            grp = mm.groups()
                            name, _, ov = grp[2].partition(",")
                            if ov == "":
                                ov = "0.0"
                            else:
                                ov = ov.strip().split()[0]

                            fow[resolve_name(name, names)] = (int(grp[0]), int(grp[1]), int(float(ov)))

            print fow

            # set fow on bat1 and bat2
            for bt in itertools.chain(bat1, bat2):
                if bt.out_type not in WICKET_SET:
                    continue
                if not hasattr(bt, 'out_over'):
                    fw = fow[bt.player]
                    bt.out_wicket_no = fw[0]
                    bt.out_score = fw[1]
                    bt.out_over = fw[2]

            write_vals(bat1, 1, team1, odi.id, summ1)

            write_vals(bat2, 2, team2, odi.id, summ2)
            print "Wrote odi : {}, inns1 = {}, inns2 = {}".format(odi, len(bat1), len(bat2))
        except Exception as ex:
            print "Error importing odi {}".format(odi)
            traceback.print_exc()
            if odi_ids is not None:
                raise
            print ex

        #if idx == 3:
        #    break

import _mysql

WICKET_SET = set(["runout", "lbw", "caught", "bowled", "stumped"])


def write_vals(bt, inns, team, odi, summ):
    """

    """
    SQL = ("INSERT INTO `score`(odi, team, player, inns, runs, balls, mins, fours, sixes, pos,"
           "`out`, out_over, out_score, out_wicket_no, out_by, out_assist) VALUES ")
    vals = []
    for bb in bt:
        row = "("
        row += '{},"{}","{}",{},{},{},'.format(odi, team, _mysql.escape_string(bb.player), inns, bb.runs, bb.balls)
        row += '{},{},{},{},'.format(bb.mins, bb.fours, bb.sixes, bb.pos)
        if bb.out_type not in WICKET_SET:
            row += '"notout",NULL,NULL,NULL,'
            row += 'NULL,NULL'
        else:
            if hasattr(bb, "out_over"):
                row += '"{}",{},{},{},'.format(bb.out_type, bb.out_over, bb.out_score, bb.out_wicket_no)
            else:
                row += '"{}",{},{},{},'.format(bb.out_type, summ[2], summ[0], summ[1])

            if hasattr(bb, 'out_by'):
                row += '"{}",'.format(bb.out_by)
            else:
                row += 'NULL,'
            if hasattr(bb, 'out_assist'):
                row += '"{}"'.format(bb.out_assist)
            else:
                row += 'NULL'
        row = row.replace('"None"', 'NULL')
        row += ')'

        vals.append(row)

    mysql_execute(SQL + ",".join(vals))


def cleanup_name(diss):
    diss = diss.replace("*", "")
    diss = diss.replace("&dagger;", "")
    return diss


def get_innings(tbl):
        trs = filt(tbl[0].findAll('tr'))
        # check columns
        heading = tbl[0].find('tr', {'class': 'inningsHead'})
        hdrs = {}
        hdridx = 3
        for td in heading.findAll('td'):
            col = td.get('title')
            if not col:
                continue
            if 'runs' in col:
                hdrs['runs'] = hdridx
                hdridx += 1
            elif 'balls' in col:
                hdrs['balls'] = hdridx
                hdridx += 1
            elif 'minutes' in col:
                hdrs['minutes'] = hdridx
                hdridx += 1
            elif 'fours' in col:
                hdrs['fours'] = hdridx
                hdridx += 1
            elif 'sixes' in col:
                hdrs['sixes'] = hdridx
                hdridx += 1

        obs = []
        for tr in trs:
            td = tr.findAll('td')
            if tr['class'] == "inningsRow":
                if "battingDetails" == td[4]['class']:
                    if "battingDismissal" != td[2]['class']:
                        continue
                    if td[1].a is None:
                        continue
                    ob = obj()
                    obs.append(ob)
                    ob.pos = len(obs)
                    ob.player = cleanup_name(td[1].text)
                    ob.playerid = os.path.basename(td[1].a['href'].partition(".")[0])
                    ob.dismissal = cleanup_name(td[2].text)
                    ob.runs = getint(td[3].text)
                    ob.mins = getint(td[4].text)
                    ob.balls = getint(td[hdrs['balls']].text)
                    if 'fours' in hdrs:
                        ob.fours = getint(td[hdrs['fours']].text)
                    else:
                        ob.fours = 0
                    if 'sixes' in hdrs:
                        ob.sixes = getint(td[hdrs['sixes']].text)
                    else:
                        ob.sixes = 0
                elif "bowlingDetails" == td[4]['class']:
                    ob = obj()
                    obs.append(ob)
                    ob.player = cleanup_name(td[1].text)
                    ob.playerid = os.path.basename(td[1].a['href'].partition(".")[0])
            elif tr['class'] == "inningsComms":
                td = tr.find('td', {'class': 'battingComms'})
                if td is not None:
                    vals = td.findAll('b')
                    if len(vals) < 2:
                        continue
                    ob.out_over = int(float(vals[0].text))
                    score, _, wicket_no = vals[-1].text.partition('/')
                    ob.out_score = int(score)
                    ob.out_wicket_no = int(wicket_no)
        return obs
