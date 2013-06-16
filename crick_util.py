
engine = None
def init_mysql(force = False):
  global engine
  if engine and not force:
    return engine
  
  from sqlalchemy import create_engine
  from sqlalchemy.event import listen

  c = { 'host': 'localhost',
            'db': 'cricket',
            'user': 'root',
            'password': 'pl0twatt'
        }
  url = "mysql://%s:%s@%s/%s" % (
    c['user'], c['password'], c['host'], c['db']
  )
  engine = create_engine(url)
  
  return engine

def mysql_connect():
  """ connect to the mysql server using config options in
      the user's home folder """
  if not engine :
    init_mysql()
  
  conn = engine.connect()
  
  return conn
def mysql_fetchall(sql, *args):
  conn = mysql_connect()
  ret = conn.execute(sql, *args)
  conn.close()  
  return ret.fetchall()

def mysql_fetchone(sql, *args):
  conn = mysql_connect()
  ret = conn.execute(sql, *args)
  conn.close()
  return ret.fetchone()

def mysql_execute(sql, *args, **kwargs):
  from sqlalchemy.exc import OperationalError
  
  retries = kwargs.get('retries', 1)
  
  tri = 1
  while tri <= retries :
    try :
      conn = mysql_connect()
      ret=conn.execute(sql, *args)
      conn.close()
      return ret
    except OperationalError, e :
      # check if e.args contains 'try restarting transaction'
      # is should take care of 1205 - lock timeout exceeded
      # 1213 - Deadlock found
      if e.args and 'try restarting transaction' in e.args[0]:
        print e.args
        print "Will retry after a sleep "
        time.sleep(2)
      else :
        raise e
  raise Exception("mysql_execute retried %s times, to no avail" % retries)
