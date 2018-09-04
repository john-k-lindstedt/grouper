# Recently done:
# - unified data format for scenes: can both read and write json files
# - implemented a way to take xml layouts from draw.io for manual scene generation
# - SID is now read from listener input 
# - implemented instructions at startup (just placeholders)
# - added reminder text to the main task

# todo:
# 
# - an algorithm for generating scene files
# 
# - get boxes and centers for the instructional example
# 
# - review state, when done with a trial with possible "redo"?
#
# - would like an interactive tutorial...
#
# - figure out the best way to handle the heads up display
# 
# - track mean response / action times. 
#   want a sense of how confident / speedy / difficult each scene is
#   means will give a sense of activity per item, 
#   controlling for simple item-count effects present in longer durations
#
# - get working on slower machines, not sure if my current drawing solution will translate well. 
#   already slows down on this one at times. needs testing.
#
# - WHOLE DIFFERENT TASK FLOW for "inheritance" investigations
#





import pyglet
import json
import os, sys
import datetime, time
import xml.etree.ElementTree as ET




colors = {
        
        #lighter cycle
        'alizarin': (231, 76, 60),
        'emerald': (46, 204, 113),
        'carrot': (230, 126, 34),
        'turquoise': (26, 188, 156),
        'sun flower': (241, 196, 15),
        'peter river': (52, 152, 219),
        'amethyst': (155, 89, 182),
        
        #darker cycle
        'pomegranate': (192, 57, 43),
        'nephritis': (39, 174, 96),
        'pumpkin': (211, 84, 0),
        'green sea': (22, 160, 133),
        'orange': (243, 156, 18),
        'belize hole': (41, 128, 185),
        'wisteria': (142, 68, 173)
        
        #original color order
        #'turquoise': (26, 188, 156),
        #'green sea': (22, 160, 133),
        #'emerald': (46, 204, 113),
        #'nephritis': (39, 174, 96),
        #'peter river': (52, 152, 219),
        #'belize hole': (41, 128, 185),
        #'amethyst': (155, 89, 182),
        #'wisteria': (142, 68, 173),
        #'wet asphalt': (52, 73, 94),
        #'midnight blue': (44, 62, 80),
        #'sun flower': (241, 196, 15),
        #'orange': (243, 156, 18),
        #'carrot': (230, 126, 34),
        #'pumpkin': (211, 84, 0),
        #'alizarin': (231, 76, 60),
        #'pomegranate': (192, 57, 43),
        #'clouds': (236, 240, 241),
        #'silver': (189, 195, 199),
        #'concrete': (149, 165, 166),
        #'asbestos': (127, 140, 141)
        }



class Logger():
    def __init__(self,header,id = "test", dl = '\t', nl = '\n', fl = 'NA', logtype="main"):
        self.header = header
        self.id = id
        self.delim = dl
        self.newline = nl
        self.filler = fl
        self.file = None
        self.logtype = logtype
        return
    
    #opens a new log and subdirectory
    def open_log(self,fn = None,subdir=True, ext = ".tsv"):
        if fn == None:
            fn = Logger.getDateTimeStamp()
        dir = os.path.splitext(os.path.basename(__file__))[0] + "_data"
        dir = dir + "/" + fn + "__" + self.id
        if not os.path.exists(dir):
            os.makedirs(dir)
        self.file = open(dir+"/"+self.logtype+"__"+fn+"__"+self.id+ext,'w')
        self.file.write(self.delim.join(self.header))
        self.file.write(self.newline)
        return
    
    #logs a given line, excluding any keywords not in the header
    def log(self,  **kwargs):
        line = [self.filler] * len(self.header) #list with filler entries
        for k, v in kwargs.items(): #if keyword in header, replace filler with value
            if k in self.header:
                line[self.header.index(k)] = str(v)
        self.file.write(self.delim.join(line)) #convert list to delimited string
        self.file.write(self.newline)
        return
    
    def close_log(self):
        self.file.close()
        
    #generates date-time stamps useful for directory and file names
    def getDateTimeStamp():
        d = datetime.datetime.now().timetuple()
        return "%d-%02.d-%02.d_%02.d-%02.d-%02.d" % (d[0], d[1], d[2], d[3], d[4], d[5])



class GroupingTask():
    
    STATES = [None,"INIT","INSTRUCT","COUNT","GROUP","REVIEW","COMPLETE"]
    STATE_INIT = 1 #unused
    STATE_INSTRUCT = 2
    STATE_COUNT = 3
    STATE_GROUP = 4
    STATE_REVIEW = 5 #unused
    STATE_COMPLETE = 6
    
    event_log_header = ['ts','SID','scene_id','group_id','state','evt_id','evt_data1','evt_data2']
    
    trial_log_header = ['ts','SID', 'scene_id', 'trial_duration', 'count_duration', 'grouping_duration', 'group_count','group_membership', 'ungrouped_items']
    
    scene_log_header = ['scene_id','box_id','x','y','w','h','l','r','b','t']
    
    
    def __init__(self, window, scene_filenames = ["default.json"], subject_id = "test"):
        self.SID = subject_id
        self.datetime = Logger.getDateTimeStamp()
        
        
        #self.state = GroupingTask.STATE_COUNT
        self.state = GroupingTask.STATE_INSTRUCT
        
        self.window = window
        self.mouse_x = 0
        self.mouse_y = 0
        self.drag_anchor_x = 0
        self.drag_anchor_y = 0
        self.dragging = False
        
        
        self.scenes = []
        self.read_scene_files(scene_filenames)
        
        self.scene_ix = 0
        
        self.start_time = time.time()
        self.trial_start_time = None
        self.count_start_time = None
        self.group_start_time = None
        
        self.evt_log = Logger(id = self.SID, header = GroupingTask.event_log_header, logtype = "events")
        self.evt_log.open_log(fn = self.datetime)
        
        self.trial_log = Logger(id = self.SID, header = GroupingTask.trial_log_header, logtype = "trials")
        self.trial_log.open_log(fn = self.datetime)
        
#         self.scene_log = Logger(header = GroupingTask.scene_log_header, logtype = "scenes")
#         self.scene_log.open_log()
#         self.log_scenes()
        
        self.write_scenes_json()
        
        self.instruct_step = 0
        
        self.instruct_text = [
            "lorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsum",
            "Borem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsum",
            "Corem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsum",
            "Dorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsumlorem ipsum"
            ]
        
        self.instruct_boxes = []
        self.instruct_centers = []
        
        self.instruct_label = pyglet.text.Label(text = self.instruct_text[0], x = window.width//2, y = window.height//2,
                                  anchor_x = "center", anchor_y = "center",
                                  color = (0,0,0,255), font_size = 50, 
                                  multiline = True, width = 0.8 * window.width, height = 0.8 * window.height)
        
        self.counting_hud = pyglet.text.Label(text = "mark group centers", x = window.width//2, y = window.height-20,
                                  anchor_x = "center", anchor_y = "top",
                                  color = (0,0,0,255), font_size = 25)
        self.grouping_hud_text = "select group members: group "
        self.grouping_hud = pyglet.text.Label(text = self.grouping_hud_text, x = window.width//2, y = window.height-20,
                                  anchor_x = "center", anchor_y = "top",
                                  color = (0,0,0,255), font_size = 25)
        
        self.final_text = pyglet.text.Label(text = "Task complete!", x = window.width//2, y = window.height//2,
                                  anchor_x = "center", anchor_y = "center",
                                  color = (0,0,0,255), font_size = 50)
        
    
    def draw(self):
        s = self.scenes[self.scene_ix]
        
        
        if self.state == GroupingTask.STATE_GROUP:
            s.draw_boxes()
            s.draw_current_center()
            if self.dragging:
                self.draw_drag()
            self.grouping_hud.draw()
        elif self.state == GroupingTask.STATE_COUNT:
            s.draw_boxes()
            s.draw_centers()
            self.counting_hud.draw()
        elif self.state == GroupingTask.STATE_INSTRUCT:
            self.instruct_label.draw()
        elif self.state == GroupingTask.STATE_COMPLETE:
            self.final_text.draw()
        
    
    def draw_drag(self):
        self.scenes[self.scene_ix].draw_drag(self.mouse_x, self.mouse_y, self.drag_anchor_x, self.drag_anchor_y)
        
    def update_mouse(self, mx, my):
        self.mouse_x = mx
        self.mouse_y = my
        
    def log_evt(self, evt_id, evt_data1 = "NA", evt_data2 = "NA"):
        self.evt_log.log(ts = time.time() - self.start_time, 
                         SID = self.SID,
                         scene_id = self.scenes[self.scene_ix].id, 
                         group_id = self.scenes[self.scene_ix].group_num,
                         state = GroupingTask.STATES[self.state],
                         evt_id = evt_id, 
                         evt_data1 = evt_data1,
                         evt_data2 = evt_data2)
    
    def log_trial(self):
        scene = self.scenes[self.scene_ix]
        
        groups = {}
        ungrouped = []
        
        for g in range(0,scene.group_num + 1):
            groups[g] = []
        
        for b in scene.boxes:
            if b.group == -1:
                ungrouped.append(b.id)
            else:
                groups[b.group].append(b.id)
        
        self.trial_log.log(ts = time.time() - self.start_time, 
                           SID = self.SID,
                           scene_id = self.scenes[self.scene_ix].id, 
                           trial_duration = time.time() - self.trial_start_time,
                           count_duration = self.group_start_time - self.count_start_time,
                           grouping_duration = time.time() - self.group_start_time,
                           group_count = len(groups),
                           group_membership = groups,
                           ungrouped_items = ungrouped)
    
#     def log_scenes(self):
#         for sx in range(len(self.scenes)):
#             for b in self.scenes[sx].boxes:
#                 self.scene_log.log(scene_id = sx, box_id = b.id,
#                                    x = b.x, y = b.y,
#                                    w = b.w, h = b.h,
#                                    l = b.l, r = b.r,
#                                    b = b.b, t = b.t,
#                                    rgb = b.rgb, a = b.alpha)
    
    def write_scenes_json(self):
        datadir = os.path.splitext(os.path.basename(__file__))[0] + "_data"
        subdir = "/" + self.datetime + "__" + self.SID
        fn = "/scenes__" + self.datetime + "__ " + self.SID + ".json"
        if not os.path.exists(datadir + subdir):
            os.makedirs(datadir + subdir)
        f = open(datadir + subdir + fn,'w')
        
        dct = {}
        
        for sx in range(len(self.scenes)):
            s = self.scenes[sx].id
            dct[s] = {}
            for b in self.scenes[sx].boxes:
                bid = str(b.id)
                dct[s][bid] = {}
                dct[s][bid]["center-x"] = b.x
                dct[s][bid]["center-y"] = b.y
                dct[s][bid]["width"] = b.w
                dct[s][bid]["height"] = b.h
                dct[s][bid]["left"] = b.l
                dct[s][bid]["right"] = b.r
                dct[s][bid]["bottom"] = b.b
                dct[s][bid]["top"] = b.t
                dct[s][bid]["red"] = b.rgb[0]
                dct[s][bid]["green"] = b.rgb[1]
                dct[s][bid]["blue"] = b.rgb[2]
                dct[s][bid]["alpha"] = b.alpha
        
        f.write(json.dumps(dct, indent=4))
        f.close()
    
    def read_scene_files(self, fns):
        for fn in fns:
            name, ext = (fn.split(".")[:-1][0], fn.split(".")[-1])
            if ext == "json":
                self.read_scenes_json(name)
            elif ext == "xml":
                self.read_scene_xml(name)
    
    def read_scenes_json(self, name):
        f = open("./scenes/json/" + name + ".json",'r')
        text = f.read()
        
        scenes = json.loads(text)
        
        #for each scene
        s_ix = 0
        for scene_id in list(scenes):
            newscene = Scene(scene_data = scenes[scene_id], id = scene_id)
            s_ix += 1
            self.scenes.append(newscene)
    
    def read_scene_xml(self, name):
        #xmltext = open("./scenes/xml/boxes.xml").read()
        tree = ET.parse("./scenes/xml/" + name + ".xml")
        root = tree.getroot()
        
        #build a dictionary to give to the Scene object
        data = {}
        
        boxid = 0
        #get all of the geometries: y is top, x is left, width and height. 
        for cell in root[0]:
            for geom in cell:
                att = geom.attrib
                left = int(att['x'])
                top = int(att['y'])
                width = int(att['width'])
                height = int(att['height'])
                
                boxname = "box" + str(boxid)
                x = left + width //2
                y = window.height - (top + height //2)
                data[boxname] = {'center-x':x,'center-y':y,'width':width,'height':height,
                                 'red':0,'green':0,'blue':0,'alpha':255}
                boxid += 1
        
        
        #create a new scene out of them
        self.scenes.append(Scene(scene_data = data, id = name))
    
    def click_select(self, mx, my):
        clicked = self.scenes[self.scene_ix].clicked(mx, my)
        
        self.log_evt(evt_id = "click_selection", evt_data1 = [mx,my], evt_data2 = clicked)
    
    def drag_start(self, mx, my):
        self.dragging = True
        self.drag_anchor_x = mx
        self.drag_anchor_y = my
        
        self.log_evt(evt_id = "drag_started", evt_data1 = [self.drag_anchor_x, self.drag_anchor_y])
    
        
    def drag_select(self):
        self.dragging = False
        boxes_selected = self.scenes[self.scene_ix].dragged(self.drag_anchor_x, self.drag_anchor_y, self.mouse_x, self.mouse_y)
        
        self.log_evt(evt_id = "drag_select",evt_data1 = [self.drag_anchor_x, self.drag_anchor_y, self.mouse_x, self.mouse_y],evt_data2 = boxes_selected)
    
    def undo_selection(self):
        deselected = self.scenes[self.scene_ix].undo_selection()
        
        self.log_evt(evt_id = "group_deselected", evt_data2 = deselected)
        
    def new_center(self, mx, my):
        new_center = self.scenes[self.scene_ix].new_center(mx, my)
        
        self.log_evt(evt_id = "center_marked", evt_data1 = new_center[0:2], evt_data2 = [new_center[2]])
        
    def undo_center(self):
        deleted = self.scenes[self.scene_ix].undo_center()
        
        if deleted:
            self.log_evt(evt_id = "center_deleted", evt_data1 = deleted[0:2], evt_data2 = [-deleted[2]])
        
    def advance(self):
        s = self.scenes[self.scene_ix]
        
        if self.state == GroupingTask.STATE_INSTRUCT:
            #either proceed to the next of the remaining instructions...
            if self.instruct_step < len(self.instruct_text)-1:
                self.instruct_step += 1
                self.instruct_label.text = self.instruct_text[self.instruct_step]
            #or begin the first trial of the task
            else:
                self.trial_start_time = time.time()
                self.count_start_time = time.time()
                self.group_start_time = None
                self.state = GroupingTask.STATE_COUNT
        
        #if we're finished counting groups, go on to membership
        if self.state == GroupingTask.STATE_COUNT:
            if len(s.centers) != 0:
                self.state = GroupingTask.STATE_GROUP
                s.group_num = 0
                self.group_start_time = time.time()
                self.grouping_hud.text = self.grouping_hud_text + str(s.group_num + 1)
                self.log_evt(evt_id = "begin_grouping")

        
        #if we're dealing with grouping
        elif self.state == GroupingTask.STATE_GROUP:
            #and we're done, proceed to the next scene
            if (s.group_num + 1) >= len(s.centers):
                self.next_scene()
            #otherwise, go to the next group
            else:
                s.group_num += 1
                self.grouping_hud.text = self.grouping_hud_text + str(s.group_num+ 1)
                self.log_evt(evt_id = "next_group")
    
    def next_scene(self):
        self.log_trial()
        #if we're all out of scenes, we're done
        if (self.scene_ix + 1) >= len(self.scenes):
            self.state = GroupingTask.STATE_COMPLETE
            self.log_evt(evt_id = "task_complete")
        else:
            self.state = GroupingTask.STATE_COUNT
            self.scene_ix += 1
            self.trial_start_time = time.time()
            self.count_start_time = time.time()
            self.group_start_time = None
            self.log_evt(evt_id = "next_scene")
        
    def prev_scene(self):
        self.scene_ix = max(self.scene_ix - 1, 0)
    
    def get_time(self):
        return time.time() - self.start_time
        
    
class Scene():
    
    def __init__(self, scene_data, id = None, centered = True, flip_v = False, flip_h = False):
        self.boxes = []
        self.read_scene_data(scene_data)
            
        self.l = 10000000
        self.r = -10000000
        self.b =  10000000
        self.t = -10000000
        self.w = 0
        self.h = 0
        
        self.id = id
        
        self.get_bounding_box()
        
        
        if centered:
            self.center_scene()
        
        self.centers = []
        self.center_id = 0
        self.group_num = -1
    
    def read_scene_data(self, scene_data):
        s = scene_data
        
        box_ID = 0
        for box in list(s):
            x = s[box]["center-x"]
            y = s[box]["center-y"]
            w = s[box]["width"]
            h = s[box]["height"]
            rgb = (s[box]["red"], s[box]["green"], s[box]["blue"])
            alpha = s[box]["alpha"]
            self.boxes.append(Box(x,y,w,h, id = box, rgb = rgb, alpha = alpha))
            box_ID += 1
    
    def get_bounding_box(self):
        for b in self.boxes:
            self.l = min(self.l, b.x-(b.w//2))
            self.r = max(self.r, b.x+(b.w//2))
            self.b = min(self.b, b.y-(b.h//2))
            self.t = max(self.t, b.y+(b.h//2))
        
        self.w = self.r - self.l
        self.h = self.t - self.b
    
    def center_scene(self):
        offset = ( (window.width  / 2) - (self.w/2) - self.l, 
                   (window.height / 2) - (self.h/2) - self.b)
        for b in self.boxes:
            b.move(offset)
             
        
    
    
    
    def draw_drag(self, x1, y1, x2, y2):
        color = colors[list(colors)[self.group_num % len(colors)]] + (100,)
        pyglet.graphics.draw(4, pyglet.gl.GL_QUADS, 
            ("v2f", [x1, y1,
                     x1, y2,
                     x2, y2,
                     x2, y1]),
            ("c4B", color + color + color + color)
            )
        
    def draw_boxes(self):
        for b in self.boxes:
            b.draw(self.group_num)
    
    def draw_centers(self):
        for c in self.centers:
            c.draw()
    
    def draw_current_center(self):
        if self.group_num < len(self.centers):
            self.centers[self.group_num].draw()
            
    def clicked(self, mx, my):
        clicked = []
        for b in self.boxes:
            cl = b.clicked(mx, my, self.group_num)
            if cl:
                clicked.append(cl)
        return clicked
    
    def dragged(self, mx, my, mdx, mdy):
        boxes_selected = []
        for b in self.boxes:
            selected = b.dragged(mx, my, mdx, mdy, self.group_num)
            if selected:
                boxes_selected.append(selected)
        return boxes_selected
    
    def undo_selection(self):
        deselected = []
        for b in self.boxes:
            if b.group == self.group_num:
                deselected.append("-" + b.id)
                b.group = -1
        return deselected
    
    def new_center(self, mx, my):
        new_center = Center(mx, my, id = self.center_id)
        self.centers.append(new_center)
        self.center_id += 1
        
        return (new_center.x, new_center.y, new_center.id)
    
    def undo_center(self):
        deleted = self.centers.pop()
        if deleted:
            self.center_id -= 1
            return (deleted.x, deleted.y, deleted.id)
        else:
            return None

class Center():
    
    def __init__(self, x, y, id = -1):
        self.x = x
        self.y = y
        self.size = 10
        self.id = id
        
        self.border = pyglet.text.Label('x', font_name = 'Arial',
                                       font_size = 45, bold = True,
                                       x = self.x, y = self.y + 11,
                                       color = (0,0,0,255),
                                       anchor_x = 'center', anchor_y = 'center')
        self.label = pyglet.text.Label('x', font_name = 'Arial',
                                       font_size = 40, bold = False,
                                       x = self.x, y = self.y + 11,
                                       color = colors[list(colors)[self.id%len(colors)]] + (255,),
                                       anchor_x = 'center', anchor_y = 'center')
        
    def draw(self):
        c = colors[list(colors)[self.id%len(colors)]] + (255,)
        
        s = self.size
        
        self.border.draw()
        self.label.draw()
        
        #draw interior fill
        #pyglet.gl.glLineWidth(15)
        #pyglet.graphics.draw(4, pyglet.gl.GL_LINES, 
        #    ("v2f", [self.x - s, self.y - s,
        #             self.x + s, self.y + s,
        #             self.x - s, self.y + s,
        #             self.x + s, self.y - s]),
        #    ("c4B", c + c + c + c)
        #    )

class Box():
    
    def __init__(self, x, y, w, h, id = -1, rgb = (0,0,0), alpha = 255):
        self.id = id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.t = int(self.y + (self.h / 2))
        self.b = int(self.y - (self.h / 2))
        self.l = int(self.x - (self.w / 2))
        self.r = int(self.x + (self.w / 2))
        self.rgb = rgb
        self.alpha = alpha
        self.selected_color = (100,100,250,255)
        self.group = -1
        self.selected = False
        self.border_width = 2
        self.border_color = (0,0,0,255)
    
    
    def draw(self, group):
    
        #draw the fill-color if this box is grouped
        if self.group != -1:
            c = colors[list(colors)[self.group % len(colors)]] + (self.alpha,)

            pyglet.graphics.draw(4, pyglet.gl.GL_QUADS, 
                ("v2f", [self.l, self.b, 
                         self.l, self.t,
                         self.r, self.t, 
                         self.r, self.b]),
                ("c4B", c + c + c + c)
            )
        
        #always draw the border
        pyglet.gl.glLineWidth(2)
        bgc = self.border_color
        pyglet.graphics.draw(8, pyglet.gl.GL_LINES, 
            ("v2f", [self.l, self.b, 
                     self.l, self.t,
                     self.l, self.t,
                     self.r, self.t, 
                     self.r, self.t, 
                     self.r, self.b,
                     self.r, self.b,
                     self.l, self.b]),
            ("c4B", bgc + bgc + bgc + bgc + bgc + bgc + bgc + bgc)
        )
        
        
    
    def move(self, offset):
        self.x += offset[0]
        self.y += offset[1]
        
        self.t = int(self.y + (self.h / 2))
        self.b = int(self.y - (self.h / 2))
        self.l = int(self.x - (self.w / 2))
        self.r = int(self.x + (self.w / 2))
    
    def clicked(self, mx, my, group):
        if mx <= self.r and mx >= self.l and my <= self.t and my >= self.b:
            self.group = group if self.group == -1 else -1
            return self.id if self.group != -1 else "-" + self.id
        else:
            return None
    
    def dragged(self, mx, my, mdx, mdy, group):
        d_t = max(my, mdy)
        d_b = min(my, mdy)
        d_l = min(mx, mdx)
        d_r = max(mx, mdx)
        
        x_overlap = max(0, min(d_r, self.r) - max(d_l, self.l))
        y_overlap = max(0, min(d_t, self.t) - max(d_b, self.b))
        
        overlap = 1.0 * x_overlap * y_overlap
        
        if overlap != 0 and self.group == -1:
            self.group = group
            return self.id
        else:
            return None

# main thread execution
if __name__ == "__main__":
    
    #get subject ID from the command line
    id_input = input("Subject ID: ")
    
    # initializing pyglet

    window = pyglet.window.Window(fullscreen=True)

    pyglet.gl.glClearColor(1,1,1,1) 

    pyglet.gl.glLineWidth(15)

    pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
    pyglet.gl.glBlendFunc(pyglet.gl.GL_SRC_ALPHA, pyglet.gl.GL_ONE_MINUS_SRC_ALPHA)
    
    
    #defining callback functions
    #  seems to need to happen after the window is defined, but before the run function is called
    #  when something happens on the pyglet window manager thread, 
    #  these functions are called in response
    
    @window.event
    def on_draw():
        window.clear()
        task.draw()
    

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE and (modifiers & pyglet.window.key.MOD_SHIFT):
            window.close()
    
        if symbol == pyglet.window.key.ENTER or symbol == pyglet.window.key.SPACE:
            if not task.dragging:
                task.advance()
    
        #state-specific actions
        if task.state == GroupingTask.STATE_COUNT:
            if symbol == pyglet.window.key.BACKSPACE:
                task.undo_center()
    
        elif task.state == GroupingTask.STATE_GROUP:
            if symbol == pyglet.window.key.BACKSPACE:
                task.undo_selection()


    #@window.event
    #def on_mouse_press(x, y, button, modifiers):
        #if task.state == GroupingTask.STATE_COUNT:
        #    task.new_center(x, y)
        #if task.state == GroupingTask.STATE_GROUP:
        #    task.click_select(x, y)

    @window.event
    def on_mouse_release(x, y, button, modifiers):
        if task.state == GroupingTask.STATE_COUNT:
            if button & pyglet.window.mouse.LEFT:
                task.new_center(x, y)
            if button & pyglet.window.mouse.RIGHT:
                task.undo_center()
    
        if task.state == GroupingTask.STATE_GROUP:
            if task.dragging:
                task.drag_select()
            else:
                task.click_select(x, y)
    
        
        
    @window.event
    def on_mouse_drag(x, y, dx, dy, button, modifiers):
        if task.state == GroupingTask.STATE_GROUP:
            if not task.dragging:
                task.drag_start(x,y)
            else:
                task.update_mouse(x,y)
        
        
    @window.event
    def on_mouse_motion(x, y, dx, dy):
        task.update_mouse(x,y)

    #pyglet.clock.schedule_interval(update, 1/120.0)

    task = GroupingTask(window, subject_id = id_input, scene_filenames = ["boxes.xml","default.json"])
    pyglet.app.run()
    
    
    
    
    
    