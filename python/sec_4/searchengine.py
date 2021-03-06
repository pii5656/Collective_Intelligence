import urllib2
from BeautifulSoup import *
from pysqlite2 import dbapi2 as sqlite
from urlparse import urljoin

# create ignoring words list
ignorewords = set(['the', 'of', 'to', 'and', 'a', 'in', 'is', 'it'])

class crawler:
  # initialize crawler with database name
  def __init__(self, dbname):
    self.con = sqlite.connect(dbname)
  
  def __del__(self):
    self.con.close()

  def dbcommit(self):
    self.con.commit()

  # auxiliary function to get entry ID or add it
  def getentryid(self, table, field, value, createnew = True):
    cur = self.con.execute(
        "select rowid from %s where %s = '%s'" % (table, field, value))
    res = cur.fetchone()
    if res == None:
      cur = self.con.execute(
          " insert into %s (%s) values ('%s')" % (table, field, value))
      return cur.lastrowid
    else:
      return res[0]

  # index pages
  def addtoindex(self, url, soup):
    if self.isindexed(url): return
    print 'Indexing ' + url

    # get words
    text = self.gettextonly(soup)
    words = self.separatewords(text)

    # get URL id
    urlid = self.getentryid('urllist', 'url', 'url')

    for i in range(len(words)):
      word = words[i]
      if word in ignorewords: continue
      wordid = self.getentryid('wordlist', 'word', word)
      self.con.execute("insert into wordlocation(urlid, wordid, location) values (%d, %d, %d)" % (urlid, wordid, i))

  # extract all text without tags from HTML
  def gettextonly(self, soup):
    v = soup.string
    if v == None:
      c = soup.contents
      resulttext = ''
      for t in c:
        subtext = self.gettextonly(t)
        resulttext += subtext + '\n'
      return resulttext
    else:
      return v.strip()

  # split to words by character, not space
  def separatewords(self, text):
    splitter = re.compile('\\W*')
    return [s.lower() for s in splitter.split(text) if s != '']

  # return true if URL has been already indexed
  def isindexed(self, url):
    u = self.con.execute("select rowid from urllist where url = '%s'" % url).fetchone()
    if u != None:
      # check the URL crawled or not
      v = self.con.execute('select * from wordlocation where urlid = %d' % u[0]).fetchone()
      if v != None: return True
    return False


  # put the link between two pages
  def addlinkref(self, urlFrom, urlTo, linkText):
    words = self.separatewords(linkText)
    fromid = self.getentryid('urllist', 'url', urlFrom)
    toid = self.getentryid('urllist', 'url', urlTo)
    if fromid == toid: return
    cur = self.con.execute("insert into link(fromid, toid) values (%d, %d)" % (fromid, toid))
    linkid = cur.lastrowid
    for word in words:
      if word in ignorewords: continue
      wordid = self.getentryid('wordlist', 'word', word)
      self.con.execute("insert into linkwords(linkid, wordid) values (%d, %d)" % (linkid, wordid))

  # receive list of pages, execute depth priority search in given depth
  # index pages
  def crawl(self, pages, depth = 2):
    pass

  # create database table
  def createindextables(self):
    pass

  def crawl(self, pages, depth = 2):
    for i in range(depth):
      newpages = set()
      for page in pages:
        try:
          c = urllib2.urlopen(page)
        except:
          print 'Could not open %s' % page
          continue
        soup = BeautifulSoup(c.read())
        self.addtoindex(page, soup)

        links = soup('a')
        for link in links:
          if ('href' in dict(link.attrs)):
            url = urljoin(page, link['href'])
            if url.find("'") != -1: continue
            url = url.split('#')[0] # remove anchor from url
            if url[0:4] == 'http' and not self.isindexed(url):
              newpages.add(url)
            linkText = self.gettextonly(link)
            self.addlinkref(page, url, linkText)
        self.dbcommit()
      pages = newpages

  def createindextables(self):
    self.con.execute('create table urllist(url)')
    self.con.execute('create table wordlist(word)')
    self.con.execute('create table wordlocation(urlid, wordid, location)')
    self.con.execute('create table link(fromid integer, toid integer)')
    self.con.execute('create table linkwords(wordid, linkid)')
    self.con.execute('create index wordidx on wordlist(word)')
    self.con.execute('create index urlidx on urllist(url)')
    self.con.execute('create index wordurlidx on wordlocation(wordid)')
    self.con.execute('create index urltoidx on link(toid)')
    self.con.execute('create index urlfromid on link(fromid)')
    self.dbcommit()
