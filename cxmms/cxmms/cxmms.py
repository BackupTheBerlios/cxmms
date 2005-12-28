import curses
import xmms
import select

debug = 1
if debug:
	file = open('/tmp/cxmms.log','w')
	log = file.write
else:
	# Set the Logger as NULL if Needed	
	log = lambda a: None

def key_strokes():
	''' This Corresponds to each Key Stroke's ASCII Value'''
	x = ord("x")
	c = ord("c")
	v = ord("v")
	z = ord("z")
	b = ord("b")
	j = ord("j")
	s = ord("s")
	q = ord("q")
	esc = 0x1b
	up = (0x1b,0x5b,0x41)
	down = (0x1b,0x5b,0x42)
	right = (0x1b,0x5b,0x43)
	left = (0x1b,0x5b,0x44)
	enter = 0x0a
	# There are 2 Backspaces, one for xterm, and one for a Linux terminal... Who knows why
	backspace = [0x08,0x7f]
	return locals()


def format_time (time):
	'''This Simply Formats the Time'''
	if time > 3600:
		return "%02d:%02d:%02d" % (time/3600, (time % 3600)/60, time % 60)
	else:
		return "%02d:%02d" % (time/60,time % 60)


class cxmms_main_window:
	def __init__(self, win, top = 6,left = 10):
		win.clear()
		
		self.win = win
		self.win.border()
		
		# This Sets the keys
		self.keys = key_strokes()

		self.timers = self.win.subwin(2, 10, top+1, left + 3)
		self.title = self.win.subwin(3, 40, top+1, left + 15)
		self.playtime = self.win.subwin(2, 40, top+4, left + 15)
		self.volume = self.win.subwin(7, 10, top+3, left + 2)
		self.shuffle = self.win.subwin(1,1,top+10, left + 5)
			
		self.windows = [self.timers, self.playtime, self.shuffle, self.volume, self.win, self.title]
		
		# This makes the set of which key is bound to which function
		key = self.keys
		self.keymaps = {
			key["x"] : xmms.play,
			key["c"] : xmms.pause,
			key["v"] : xmms.stop,
			key["z"] : xmms.playlist_prev,
			key["b"] : xmms.playlist_next,
			key["s"] : xmms.toggle_shuffle,
			key["up"] : lambda : xmms.set_main_volume(min(100, xmms.get_main_volume() + 10)),
			key["down"] : lambda : xmms.set_main_volume(max(0, xmms.get_main_volume() - 10)),
			key["right"] : lambda : xmms.jump_to_time(xmms.get_output_time()+5000),
			key["left"] : lambda : xmms.jump_to_time(max(0,xmms.get_output_time()-5000))
		};

	def update(self):
		'''This Refreshes the Screen... It calculates times and such, and then draws'''
		time = xmms.get_output_time()/1000
		num = xmms.get_playlist_pos()
		title = xmms.get_playlist_title(num)
		shuffle = xmms.is_shuffle()
		length = xmms.get_playlist_time(num) / 1000
		
		self.win.border()
		
		self.shuffle.clear()
		if shuffle:
			self.shuffle.insstr(0,0,"S")
		
		t = format_time(time)
		self.timers.clear()
		self.timers.addstr(t)
		
		self.title.clear()
		self.title.addstr("%d. %s (%s)" % (num,title,format_time(length)))

		t = (time * 40) / length
		self.playtime.clear()
		self.playtime.insstr(0,0,'.' * t)
		self.playtime.insstr(0, min(t,39), '%',curses.A_BOLD)
		if t < 39:
			self.playtime.insstr(0,t+1,'.' * (39 -t))

		self.volume.clear()
		v = xmms.get_main_volume()
		self.volume.insstr(0,0, 'Vol: %2d' % (v))

		v = int(round(v / 10))
		for i in range(0, 5):
			if (i * 2 < v):
				self.volume.hline(6-i, 0, '#', 2*i-1, curses.A_BOLD)
			else:
				self.volume.hline(6-i, 0, '_', 2*i-1)
				
# 		# gratuitous use of lambda
		map(lambda a: a.refresh(), self.windows)
	
	def pass_keystroke(self,key):
		'''This Accepts the Keystroke from the Window Manager, and Returns
		instructions on what to do next'''
		if key == self.keys["q"]:
			return "quit"
		if key == self.keys["j"]:
			return "search"
		else:
			if self.keymaps.has_key(key):
				self.keymaps[key]()
				return None

class cxmms_jump(cxmms_main_window):
	
	def __init__(self, stdscr, top = 6,left = 10):
		cxmms_main_window.__init__(self,stdscr,top,left)
		self.jump = self.win.subwin(6, 45, top+6, left + 12)
		self.windows.insert(0,self.jump)
		self.string = ""
		
		# song contains the song that will play if you press enter NOW
		self.song = -1
		
		# Highlight and Base choose which part of search space to look at
		self.base = 0
		self.highlight = 0
		
		self.draw_jump(self.string)
		
	def songs_that_match(self,string):
		'''This Returns a List of Songs that Match a Pattern'''
		songs = []
		for i in range(xmms.get_playlist_length()):
			if string.lower() in xmms.get_playlist_title(i).lower():
				songs.append(i)
		return songs
						
	def draw_jump(self,string):
		'''This Draws Jump.... But also returns highlighted Song'''
		self.jump.clear()
		self.jump.insstr(1,2,"Search: %s" % string)
		self.song_list = self.songs_that_match(string)
		
		# This tries to get a particular slice
		try:
			print_slice = self.song_list[self.base:self.base+3]
		except:
			print_slice = self.song_list[:3]

		i = 2
		
		for j in print_slice:
			# This next Line Selects if it should be formatted
			if self.highlight + 2 == i:
				style = curses.A_STANDOUT
			else:
				style = curses.A_NORMAL
			self.jump.insstr(i,2,xmms.get_playlist_title(j)[:42],style)
			i = i + 1
			
		self.jump.border()
		
		# this next block returns the highlighted song. If there is none, then
		# it returns -1
		try:
			return print_slice[self.highlight]
		except:
			return -1

	def pass_keystroke(self,key):
		'''This Accepts a KeyStroke from the WM and returns instruction on
		what the WM should do next, ex: close the jump function'''
		self.jump.clear()
		
		# select() rocks, timeout == 1 sec
		if key == self.keys["esc"]:
			self.win.clear()
			return "search_finished"
		
		if key == self.keys["enter"]:
			if self.song != -1:
				xmms.set_playlist_pos(self.song)
				self.win.clear()
				return "search_finished"
		
		if key == self.keys["up"]:
			if self.highlight != 0:
				self.highlight = max(self.highlight - 1,0)
			else:
				self.base = max(self.base - 1, 0)
		
		if key == self.keys["down"]:
			if self.highlight != 2:
				self.highlight = min(self.highlight + 1,len(self.song_list) - 1)
			else:
				self.base = min(self.base + 1, len(self.song_list) - 3)
			
		if key in self.keys["backspace"]:
			self.highlight = 0
			self.base = 0
			self.string = self.string[:-1]
		else:
			# If key is a tuple, we do not want a crash over here
			try:
				self.string = self.string + chr(key)
				self.highlight = 0
				self.base = 0
			except:
				pass
			
		self.song = self.draw_jump(self.string)

class cxmms_window_manager:
	
	def __init__(self, stdscr, top = 6,left = 10):
		'''This Function Simply Declares the WM'''
		
		# Next two lines declare the space used on screen
		self.stdscr = stdscr
		self.win = curses.newwin(13, 60, top, left)
		
		# This next block sets the active window
		self.active = cxmms_main_window(self.win,top,left)
	
	def keyloop(self):
		
		'''This is the Loop that does Work It Accepts input, 
		and passes it to the active object. The Active object
		will in turn return a message. This WM decides what to
		do with that particular message'''
		
		message = None
		
		# Infinite Loop
		while True:
			
			# This Updates the active window
			self.active.update()
			# select() rocks, timeout == 1 sec
			(read, write, err) = select.select([0], [], [], 1)
			
			# If a key is pressed, read will be a list with 0 in it
			if 0 in read:
				key = self.get_key()
				
				try:
					log("key pressed: 0x%02x %c" % (key,chr(key)))
				except:
					log("key pressed: %s" % str(key))
				
				# message is returned by active window and is saved
				message = self.active.pass_keystroke(key)
				log("\tmessage returned: %s\n"  % message)
				
			# The Next Blocks checks for special messages, ie. when active object
			# should be changed
			
			if message == "search":
				self.active = cxmms_jump(self.win)
				message = None
				
			if message == "search_finished":
				self.active = cxmms_main_window(self.win)
				message = None
				
			if message == "quit":
				break
	
	def get_key(self):
		key = self.win.getch()
		
		# special exceptions for arrow keys
		if key == 0x1b:
			(read, write, err) = select.select([0], [], [], 0)
			if 0 in read:
				if self.win.getch() == 0x5b:
					key = (0x1b,0x5b,self.win.getch())
		
		return key

def logo(stdscr):
        str = ".::Commandline XMMS::."
        stdscr.insstr(3, 40-len(str)/2, str)
        stdscr.refresh()

        copyright = "(C) 2005, Blug.in"
        stdscr.insstr(20, 70-len(copyright), copyright)
        stdscr.refresh()

def main(stdscr):
        curses.savetty()
        try:
                logo(stdscr)
                w = cxmms_window_manager(stdscr)
                w.keyloop()
        finally:
                curses.resetty()

curses.wrapper(main)