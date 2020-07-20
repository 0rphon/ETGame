import win32gui
import win32process
import pymem
from subprocess import call
from pynput.keyboard import Key, Listener
from threading import Thread
from time import sleep



######################################################################
#       GLOBALS                                                      #
#memory=info on target memory locations                              #
#       dict{target:[[base, offsets], curVal, minVal, type, address]}#
#exitFlag=tells threads when to exit. set True when end key pressed  #
#dll=target dll name                                                 #
#handle=handle to pymem debugger                                     #
######################################################################



############################################
#       INITALIZE                          #
#finds target process and connects pymem   #
#           IN                             #
#window=game window name                   #
#dll=target dll name                       #
#           OUT                            #
#handle=handle to debugged process         #
############################################
def initialize(window,dll):
    hWnd = win32gui.FindWindow(0, (window))                             #get window handle
    if(hWnd):                                                           #if window exists
        pid=win32process.GetWindowThreadProcessId(hWnd)[1]              #pid=int Process ID
        handle = pymem.Pymem()                                          #handle=pymem obj
        handle.open_process_from_id(pid)                                #handle=debugged target process
        return handle                                                   #return handle to debugged process
    else:                                                               #if window not found
        print("Process not found")                                      #tell user
        exit()                                                          #exit



###############################################
#       GET_ADDRESS                           #
#returns address pointed to by dynamic pointer#
#           IN                                #
#dll=target dll name                          #
#offsets=list of [base,offsets]               #
#handle=handle to pymem debugger              #
#           OUT                               #
#returns target address                       #
###############################################
def get_address(dll,offsets,handle):
    for mod in handle.list_modules():                               #iterate list of modules
        if(mod.name==dll):                                          #if module name == target dll name
            address=mod.lpBaseOfDll                                 #address == target module base address

    for offset in offsets[:-1]:                                     #iterate up to last offset in list of offsets
        address=handle.read_bytes(address+offset,8)                 #address= current pointer address    hex big endian
        address=int.from_bytes(address, byteorder='little')         #convert address to dec
    return(address+offsets[-1])                                     #return target address



######################################
#       GET_DATA                     #
#reads bytes in memory               #
#          IN                        #
#dll=target dll name                 #
#offsets=list of [base,offsets]      #
#data_type=name of val type in memory#
#handle=handle to pymem debugger     #
#         OUT                        #
#address=target address              #
#value=value stored at target address#
######################################
def get_data(dll,offsets,data_type,handle):
    try:
        address=get_address(dll,offsets,handle)                     #address= pointer address
        if data_type=="single":                                     #if target data is single
            value=handle.read_bytes(address,4)                      #value=bytes at pointer address
            value=int.from_bytes(value, byteorder='little')         #convert value to int
        elif data_type=="float":                                    #if target data is float
            value=handle.read_float(address)                        #value=float at pointer address
    except: address,value=False,False                               #if target not found address,value = false
    return (address,value)                                          #return address,value



######################################
#       WRITE_DATA                   #
#writes bytes to memory              #
#           IN                       #
#dll=target dll name                 #
#offsets=list with offsets           #
#src=data to write                   #
#data_type=name of val type in memory#
#handle=handle to pymem debugger     #
######################################
def write_data(dll,offsets,src,data_type,handle):
    try:
        address=get_address(dll,offsets,handle)         #address=pointer address
        if data_type=="single":                         #if writing single
            handle.write_int(address,src)               #write src to address as int
        elif data_type=="float":                        #if writing float
            handle.write_float(address,src)             #write float to address
    except: pass                                        #if unable to write: pass



#####################
#   active_memory   #
#handles input based#
#writing of memory  #  
#####################
def active_memory():

    #################################
    #      on_press                 #
    #writes to memory based on input#
    #sets exitFlag=True on Key.end  #
    #################################
    def on_press(key):
        global exitFlag
        if key==Key.right:                                                                      #if right arrow pressed
            write_data(dll, memory["x"][0], memory["x"][1]+10, memory["x"][3],handle)           #add 10 to character x position
        elif key==Key.left:                                                                     #if left arrow pressed
            write_data(dll, memory["x"][0], memory["x"][1]-10, memory["x"][3],handle)           #dec 10 to character x position
        elif key==Key.up:                                                                       #if up arrow pressed
            write_data(dll, memory["y"][0], memory["y"][1]+10, memory["y"][3],handle)           #add 10 to character y position
        elif key==Key.down:                                                                     #if down arrow pressed
            write_data(dll, memory["y"][0], memory["y"][1]-10, memory["y"][3],handle)           #dec 10 to character y position
        elif key == Key.end:                                                                    #if end key pressed
            exitFlag=True                                                                       #tell all thread to exit
            return False                                                                        #tell keyboard listener to exit

    with Listener(on_press=on_press) as listener:           #activate pynput keyboard listener
        listener.join()                                     #wait for listener threads to exit



################################################
#               passive_memory                 #
#handles passive reading and writing of memory #
#and updates memory dict accordingly           #
################################################
def passive_memory():
    while exitFlag==False:                                                                                                          #while not exit
        for targetValName, targetValVars in memory.items():                                                                         #for key, values in memory map
            memory[targetValName][4], memory[targetValName][1] = get_data(dll, targetValVars[0], targetValVars[3],handle)           #update address and value
            if targetValVars[2] != -1 and memory[targetValName][1] < targetValVars[2]:                                              #if target has minVal and curVal < minVal
                write_data(dll, targetValVars[0], targetValVars[2], targetValVars[3],handle)                                        #write_data(dllName,offset,minVal,type)



######################################################################
#       update screen                                                #
#calls cls then prints current target memory info to screen          #
#           IN                                                       #
#memory=info on target memory locations                              #
#       dict{target:[[base, offsets], curVal, minVal, type, address]}#
######################################################################
def update_screen(memory):
    call("cls",shell=True)                                                  #clear cmd
    for targetValName,targetValItems in memory.items():                     #for value in memory
        print(targetValName + (" "*(10-len(targetValName))) +
            str(hex(targetValItems[4])), str(targetValItems[1]))            #print target, address, curVal



###############
#Main Function#
###############
def main():
    global memory,exitFlag,dll,handle
    window="Enter the Gungeon"                      #window=game window name
    dll="UnityPlayer.dll"                           #dll=target dll name
    handle=initialize(window,dll)                   #connect pymem debugger to the target process
    memory={                                        #dict{target:[[base, offsets], curVal, minVal, type, address]}
        "x":[[0x0144EBB8,0x8,0x98,0x28,0x30,0x18,0xC8,0x170],0,-1,"single",0],
        "y":[[0x0144EBB8,0x8,0x98,0x28,0x30,0x18,0xC8,0x174],0,-1,"single",0],
        "money":[[0x0144EBB8,0x8,0x40,0x80,0x28,0x30,0x198,0x1C],0,9999,"single",0],
        "keys":[[0x0144EBB8,0x8,0x40,0x80,0x28,0x30,0x198,0x20],0,99,"single",0],
        "ammo":[[0x0144EBB8,0x8,0x98,0x28,0x30,0x278,0x28,0x3B0],0,999999,"single",0],
        "blanks":[[0x0144EBB8,0x8,0x10,0x30,0x48,0x28,0x30,0x568],0,20,"single",0],
        "health":[[0x0144EBB8,0x8,0x98,0x28,0x30,0x18,0x50,0x118],0.0,20.0,"float",0],
        "hearts":[[0x0144EBB8,0x8,0x98,0x28,0x30,0x18,0x50,0x114],0.0,20.0,"float",0]
    }

    exitFlag=False
    Thread(target=active_memory).start()            #start active_memory thread
    Thread(target=passive_memory).start()           #start passive_memory thread
    while exitFlag==False:                          #while not exit
        update_screen(memory)                       #update values on screen
        sleep(0.1)                                  #sleep 0.1 seconds



##########
#Run Main#
##########
if __name__=="__main__":
    try:
        main()
    except Exception as e:              #if exception
        print("Error: %s"%e)            #print error
        exit()                          #exit
