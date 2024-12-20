from socket import socket, AF_INET, SOCK_STREAM
from tkinter import *
from tkinter import ttk
from typing import Callable
from threading import Thread
from datetime import datetime

class Server:
    def __init__(self) -> None:
        self._socket: socket | None = None # socket object for communication
        self.connected = False # connection status
    def connect(self, host: str, port: int):
        self._socket = socket(AF_INET, SOCK_STREAM) # create a TCP/IP socket
        self.connected = self._socket.connect_ex((host, port)) == 0 # attempt connection
    def disconnect(self):
        self.connected = False
        if self._socket:
            self._socket.close()
            self._socket = None
    # send a message to the server
    def send(self, msg: str) -> None:
        if not self._socket:
            raise RuntimeError("Socket not connected")
        fmsg = f"{msg}\n" # append newline
        print(f"> {msg}")
        self._socket.sendall(fmsg.encode('utf-8')) # send encoded message 
    # listen for incoming messages from the server 
    def listen(self, handle: Callable[[str], None]) -> Thread:
        if not self._socket:
            raise RuntimeError("Socket not connected")
        def listen_thread():
            buffer = "" # buffer for partial messages 
            while self.connected:
                data: str
                try:
                    # receive and decode data 
                    data = self._socket.recv(1024).decode('utf-8')
                except Exception as e:
                    # handle connection errors 
                    self.connected = False
                    self._socket = None
                    break
                if not data: # if no data received, server closes connection 
                    break # Socket closed by server
                buffer += data
                while '\n' in buffer: # process complete messages 
                    message, buffer = buffer.split('\n', 1)
                    print(f"! {message}")
                    handle(message)
       # start listening in a separate thread
        listener = Thread(target=listen_thread, daemon=True)
        listener.start()
        return listener
# functions to create queries for the server
def createGroupsQuery() -> str:
    return "GROUPS"
def createJoinQuery(group: str, name: str) -> str:
    return f"JOIN|{group}|{name}"
def createLeaveQuery(group: str) -> str:
    return f"LEAVE|{group}"
def createPostQuery(group: str, subject: str, content: str) -> str:
    return f"POST|{group}|{subject}|{content}"
def createViewQuery(group: str, id: int) -> str:
    return f"VIEW|{group}|{id}"
def createExitQuery():
    return 'EXIT'

# functions to parse server responses 
def parseGroupsMsg(msg: str):
    # GROUPS|g1|g2|g3|...
    return msg.split("|")[1:]
def parseJoinMsg(msg: str) -> tuple[str, str]:
    # JOIN|group|name
    parts = msg.split("|")
    return [parts[1], parts[2]]
def parseLeaveMsg(msg: str) -> tuple[str, str]:
    # LEAVE|group|name
    parts = msg.split("|")
    return [parts[1], parts[2]]
def parseMessageMsg(msg: str) -> tuple[str, int]:
    # MESSAGE|group|id
    parts = msg.split("|")
    return [parts[1], int(parts[2])]
def parseViewMsg(msg: str) -> tuple[str, int, str, datetime, str, str]:
    # VIEW|group|id|sender|postDate|subject|contents
    parts = msg.split("|")
    return [parts[1], int(parts[2]), parts[3], datetime.fromisoformat(parts[4]), parts[5], parts[6]]

# connectionframe manages connection input and setup GUI
class ConnectionFrame(Frame):
    def __init__(self, parent, onConnected: Callable[[], None]) -> None:
        Frame.__init__(self, parent)
        # input fields 
        self._onConnected = onConnected
        self._userNameVar = StringVar()
        self._userNameLabel = Label(self, text="User Name")
        self._userNameEntry = Entry(self, textvariable=self._userNameVar)
        self._hostVar = StringVar()
        self._hostLabel = Label(self, text="Host")
        self._hostEntry = Entry(self, textvariable=self._hostVar)
        self._portVar = StringVar()
        self._portLabel = Label(self, text="Port")
        self._portEntry = Entry(self, textvariable=self._portVar)
        self._connectButton = Button(self, text="Connect", command=self._handleConnect)
        self._placeFrames()
    # arrange components in grid 
    def _placeFrames(self):
        self._userNameLabel.grid(row=0, column=0)
        self._userNameEntry.grid(row=0, column=1)
        self._hostLabel.grid(row=1, column=0)
        self._hostEntry.grid(row=1, column=1)
        self._portLabel.grid(row=2, column=0)
        self._portEntry.grid(row=2, column=1)
        self._connectButton.grid(row=3, column=0, columnspan=2)
    def _handleConnect(self):
        host = self._hostVar.get()
        portStr = self._portVar.get()
        if self._hostVar.get() == "" or self._portVar.get() == "":
            return # do nothing if host or port is empty 
        server.connect(host, int(portStr))
        if (server.connected):
            self._onConnected() # callback if connected 
    def getUserName(self) -> str: return self._userNameVar.get()

# represents the main frame of the application
class MainFrame(Frame):
    def __init__(self, parent: Tk, userName: str) -> None:
        Frame.__init__(self, parent)
        self.userName = userName
        self._joinFrame = JoinFrame(self, [], userName) # Create join frame
        self._sep = ttk.Separator(self, orient='horizontal') # Create separator
        self._groups = GroupsFrame(self, self._handleLeaveClicked) # Create groups frame
        self._msgFrame = MessagingFrame(self, self._handlePostClicked) # Create msg frame
        self._placeFrames() # arrange the components of the main frame
        server.send(createGroupsQuery()) # Send a query for groups to begin
        parent.title(userName) # set the username
    def _placeFrames(self):
        self._joinFrame.grid(row=0, column=0) # Place join frame
        self._sep.grid(row=1, column=0) # Place separator
        self._groups.grid(row=2, column=0) # Place groups frame
        self._msgFrame.grid(row=3, column=0) # Place msg frame
    def _handlePostClicked(self, subject: str, content: str): # handles a post button click event from the messaging frame
        server.send(createPostQuery(self._groups.current()[0], subject, content)) # sends a post query to the server
    def _handleLeaveClicked(self, group: str): # handles a leave button click event from the details frame
        server.send(createLeaveQuery(group)) # send a leave query to the server
    def handleGroups(self, groups: list[str]): # handles a response from a groups query
        for g in groups:
            self._joinFrame.add(g) # Add the group to the joinable groups
        if "Public" in groups:
            server.send(createJoinQuery("Public", self.userName)) # automatically send a query to join the Public group
    def handleJoin(self, group: str, name: str):
        """Handles a join event"""
        if name == self.userName: # we have successfully joined the group
            self._joinFrame.remove(group) # remove joined group from joinable group selector
            f = self._groups.add(group) # create new group frame
            if f is not None:
                f.add_user(name) # add current user to the frame
        else: # someone else joined a group we are in
            frame = self._groups.groups.get(group) # get the frame of the associated group
            if frame is not None:
                frame.add_user(name) # add the user to users of the group's frame
    def handleLeave(self, group: str, name: str):
        """Handles a leave event"""
        if name == self.userName: # we have successfully left a group
            self._joinFrame.add(group) # add the group back to the list of joinable groups
            self._groups.remove(group) # remove the current group from the active groups
        else: # someone else has left a group we are in
            frame = self._groups.groups.get(group) # get the associated frame
            if frame is not None:
                frame.remove_user(name) # remove the user from the group's frame
    def handleMessage(self, group: str, msgId: int):
        """Handles a message notification"""
        frame = self._groups.groups.get(group) # get the associated group's frame
        if frame is None:
            return
        frame.add_msg(msgId) # add the msg to the group
    def handleView(self, group: str, id: int, sender: str, post_date: datetime, subject: str, content: str):
        """Handles a view response for a msg"""
        frame = self._groups.groups.get(group) # get the associated group's frame
        if frame is None:
            return
        frame.add_msg_contents(id, sender, post_date, subject, content) # populate the details 
    def exit(self):
        """Sends an exit request to the server to close the connection"""
        server.send(createExitQuery())

# represents the selector and button of groups that can be joined
class JoinFrame(Frame):
    def __init__(self, parent, groups: list[str], userName: str) -> None:
        Frame.__init__(self, parent)
        self._groups = groups
        self._userName = userName
        self._currentGroup = StringVar()
        self._groupBox = ttk.Combobox(self, textvariable=self._currentGroup, values=self._groups)
        self._joinButton = Button(self, text="Join", command=self._handleJoinClicked)
        self._placeFrames() # arrange frames
    def _placeFrames(self):
        # define arrangement of controls
        self._groupBox.grid(row=0, column=0)
        self._joinButton.grid(row=0, column=1)
    def _handleJoinClicked(self) -> None: # handles the join button being clicked
        group = self._currentGroup.get()
        if group != "":
            q = createJoinQuery(group, self._userName) # create a join query
            server.send(q) # send the join query
    def add(self, group: str):
        """adds a group to the list"""
        if group in self._groups:
            return
        self._groups.append(group)
        self._groupBox['values'] = self._groups
    def remove(self, group: str):
        """removes a group from the list"""
        if group not in self._groups:
            return
        self._groups.remove(group)
        self._groupBox['values'] = self._groups
        if group == self._currentGroup.get():
            self._currentGroup.set("")

# represents a collection of active groups the user is in
class GroupsFrame(Frame):
    def __init__(self, parent, onLeave: Callable[[str], None]):
        Frame.__init__(self, parent)
        self._onLeave = onLeave
        self._nb = ttk.Notebook(self) # tabs control
        self._nb.grid(row=0, column=0)
        self.groups: dict[str, GroupFrame] = {} # internal mapping from groupname to the associated child frames
    def current(self):
        """Gets the currently selected group name and group frame"""
        name = self._nb.tab(self._nb.select(), 'text')
        return name, self.groups[name]
    def add(self, groupName: str):
        """Adds a new active group by name"""
        if groupName in self.groups:
            return
        frame = GroupFrame(self._nb, groupName, lambda: self._onLeave(groupName))
        self._nb.add(frame, text=groupName)
        self.groups[groupName] = frame
        return frame
    def remove(self, groupName: str):
        """Removes an active group by name"""
        if groupName not in self.groups:
            return
        frame = self.groups[groupName]
        self._nb.forget(frame)
        del self.groups[groupName]

# represents a single active group pane
class GroupFrame(Frame):
    def __init__(self, parent, name: str, onLeave: Callable[[], None]):
        Frame.__init__(self, parent)
        self.name = name
        self._messages: dict[int, tuple[str, datetime, str, str] | None] = {} # declare data structure for holding the user's history of messages for this group
        self._users = UsersFrame(self)
        self._messagesFrame = MessagesFrame(self, self._handleMsgSelectionChanged)
        self._details = DetailFrame(self, onLeave)
        self._placeFrames() # arrange the controls
    def _placeFrames(self):
        # define how controls are arranged
        self._users.grid(row=0, column=0)
        self._messagesFrame.grid(row=0, column=1)
        self._details.grid(row=0, column=2)
    def _handleMsgSelectionChanged(self, msgId: int | None): # handle a change of what message the user is currently selecting
        if msgId is None:
            self._details.clear() # clear details if no msg is selected
            return
        msgTuple = self._messages.get(msgId) # try to find stored message
        if msgTuple is None: # if msgid is found but no details
            self._details.clear() # clear details
            server.send(createViewQuery(self.name, msgId)) # send view query to request details
            return
        # otherwise, populate details
        self._details.setSender(msgTuple[0])
        self._details.setFromDate(msgTuple[1])
        self._details.setSubject(msgTuple[2])
        self._details.setContent(msgTuple[3])
    def add_user(self, user: str):
        """Adds a visible user to the group"""
        self._users.add(user)
    def remove_user(self, user: str):
        """Removes a visible user from the group"""
        self._users.remove(user)
    def add_msg(self, id: int):
        """Adds a message of a specific id to the messages pane"""
        self._messages[id] = None
        self._messagesFrame.add(id)
    def add_msg_contents(self, id: int, sender: str, post_date: datetime, subject: str, content: str):
        """Adds view response contents to the associated message"""
        self._messages[id] = [sender, post_date, subject, content] # add details to the data structure
        curr = self._messagesFrame.current()
        if id == curr: # check if the message is currently selected
            # populate fields if the message is currently selected
            self._details.setSender(sender)
            self._details.setFromDate(post_date)
            self._details.setSubject(subject)
            self._details.setContent(content)
    
# represents the list of active users in a group
class UsersFrame(LabelFrame):
    def __init__(self, parent):
        LabelFrame.__init__(self, parent, text="Users")
        self._usersBox = Listbox(self)
        self._scroll = Scrollbar(self)
        # configure scrolling
        self._scroll.config(command=self._usersBox.yview)
        self._usersBox.config(yscrollcommand=self._scroll.set)
        self._placeFrames()
    def _placeFrames(self):
        self._usersBox.pack(side='left', fill='both', expand=True)
        self._scroll.pack(side='right', fill='y')
    def add(self, userName: str):
        """Add a user to the active users in the group"""
        items = self._usersBox.get(0, END)
        if userName in items:
            return
        self._usersBox.insert(END, userName)
    def remove(self, userName: str):
        """Removes a user from the list of active users in the group"""
        items: list[str] = self._usersBox.get(0, END)
        if userName not in items:
            return
        try:
            index = items.index(userName)
        except ValueError:
            return
        self._usersBox.delete(index)

# represents the list of messages received for a specific group
class MessagesFrame(LabelFrame):
    def __init__(self, parent, onMessageSelectionChanged: Callable[[int | None], None]):
        LabelFrame.__init__(self, parent, text="Messages")
        self._onMessageSelectionChanged = onMessageSelectionChanged
        # create components
        self._messagesBox = Listbox(self, selectmode='single')
        self._scroll = Scrollbar(self)
        self._messagesBox.bind("<<ListboxSelect>>", self._onListboxSelect) # bind selection event
        # configure scrolling
        self._messagesBox.config(yscrollcommand=self._scroll.set)
        self._scroll.config(command=self._messagesBox.yview)
        self._placeFrames() # place frames
    def _placeFrames(self):
        self._messagesBox.pack(side='left', fill='both', expand=True)
        self._scroll.pack(side='right', fill='y')
    def current(self):
        """Get the currently selected message id, if selected"""
        indices = self._messagesBox.curselection()
        if len(indices) <= 0:
            return None
        index = indices[0]
        item: str = self._messagesBox.get(index)
        return int(item)
    def _onListboxSelect(self, _):
        """Handle a selection event from the listbox"""
        self._onMessageSelectionChanged(self.current())
    def add(self, messageId: str):
        """Add a new message id to the list"""
        self._messagesBox.insert(END, str(messageId))

# represents the details of a selected message
class DetailFrame(Frame):
    def __init__(self, parent, onLeave: Callable[[], None]):
        Frame.__init__(self, parent)
        self._senderVar = StringVar()
        self._senderLabel = Label(self, text="From: ")
        self._senderEntry = Entry(self, textvariable=self._senderVar, state=['readonly'])

        self._dateVar = StringVar()
        self._dateLabel = Label(self, text="Date: ")
        self._dateEntry = Entry(self, textvariable=self._dateVar, state=['readonly'], width=20)

        self._subjectVar = StringVar()
        self._subjectLabel = Label(self, text="Subject: ")
        self._subjectEntry = Entry(self, textvariable=self._subjectVar, state=['readonly'])

        self._content = Text(self, width=20, height=5)
        self._leaveButton = Button(self, text="Leave", command=onLeave)

        self._placeFrames() # arrange frames
    def _placeFrames(self):
        # define how frames are arranged
        self._senderLabel.grid(row=0, column=0)
        self._senderEntry.grid(row=0, column=1)

        self._dateLabel.grid(row=1, column=0)
        self._dateEntry.grid(row=1, column=1)

        self._subjectLabel.grid(row=2, column=0)
        self._subjectEntry.grid(row=2, column=1)

        self._content.grid(row=3, column=0, columnspan=2)
        self._leaveButton.grid(row=4, column=0, columnspan=2)
    def setSender(self, val: str = ""):
        self._senderVar.set(val)
    def setFromDate(self, val: datetime | None = None):
        self._dateVar.set(val.astimezone().strftime("%I:%M:%S %p, %b %d, %Y") if val is not None else "") # localize and format post date nicely
    def setSubject(self, val: str = ""):
        self._subjectVar.set(val)
    def setContent(self, val: str = ""):
        self._content.delete("1.0", END) # Clear
        self._content.insert(END, val) # Set new
    def clear(self):
        """clear all the entries"""
        self.setSender()
        self.setFromDate()
        self.setSubject()
        self.setContent()

# represents the control used to create a new post for the currently selected active group
class MessagingFrame(Frame):
    def __init__(self, parent, onPostClicked: Callable[[str, str], None]):
        Frame.__init__(self, parent)
        self._onPostClicked = onPostClicked
        self._subjectVar = StringVar()
        self._subjectLabel = Label(self, text="Subject")
        self._subjectEntry = Entry(self, textvariable=self._subjectVar)
        self._contentVar = StringVar()
        self._contentLabel = Label(self, text="Content")
        self._contentEntry = Entry(self, textvariable=self._contentVar)
        self._postButton = Button(self, text="Post", command=self._handlePostClicked)
        self._placeFrames()
    def _placeFrames(self):
        self._subjectLabel.grid(row=0, column=0)
        self._subjectEntry.grid(row=0, column=1)
        self._contentLabel.grid(row=0, column=2)
        self._contentEntry.grid(row=0, column=3)
        self._postButton.grid(row=0, column=4)
    def _handlePostClicked(self):
        subject = self._subjectVar.get()
        content = self._contentVar.get()
        if subject == "" or content == "": # validation check
            return
        self._onPostClicked(subject, content) # callback when the post button is clicked
        self._clearEntries() # clear entries once posted
    def _clearEntries(self):
        self._subjectEntry.delete(0, END)
        self._contentEntry.delete(0, END)

# a handler for receiving raw text notifications from the server
def onResponseReceived(main: MainFrame, response: str):
    # check all possible message types by their prefix
    if response.startswith("GROUPS|"):
        groups = parseGroupsMsg(response) # parse
        main.handleGroups(groups) # handle in main
    elif response.startswith("JOIN|"):
        group, name = parseJoinMsg(response) # parse
        main.handleJoin(group, name) # handle in main
    elif response.startswith("LEAVE|"):
        group, name = parseLeaveMsg(response) # parse
        main.handleLeave(group, name) # handle in main
    elif response.startswith("MESSAGE|"):
        group, msgid = parseMessageMsg(response) # parse
        main.handleMessage(group, msgid) # handle in main
    elif response.startswith("VIEW|"):
        group, id, sender, post_date, subject, content = parseViewMsg(response) # parse
        main.handleView(group, id, sender, post_date, subject, content) # handle in main

# Define a method to handle the ui connecting
def onConnected():
    userName = conn.getUserName() # fetch the user name from the connection frame
    global main
    main = MainFrame(root, userName) # Create the main frame
    server.listen(lambda msg : onResponseReceived(main, msg)) # start listening for server messages
    conn.destroy() # Remove the connection frame
    main.grid(row=0, column=0) # Place the main frame

# Initialize some global variables
server = Server()

root = Tk() # Initialize the GUI
root.title("Client") # set the title

conn = ConnectionFrame(root, onConnected) # create connection frame, with onConnected success handler
conn.grid(row=0, column=0) # place the connection frame in root

# Define a close function when exiting
def onClosing():
    if server.connected:
        if main is not None:
            main.exit() # call on main to notify server of leaving
        server.disconnect() # close the socket
    root.destroy() # close the ui window

root.protocol("WM_DELETE_WINDOW", onClosing) # Register the function handler
root.mainloop()
