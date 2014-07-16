import fabfile

class Commands():

  @staticmethod
  def execute(host, name, ip):
    try:
      fabfile.command(host, name, ip)
    except Exception, e:
      print 'Error in execute fabric command: {}'.format(e)
