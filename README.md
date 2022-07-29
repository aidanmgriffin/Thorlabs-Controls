# thorlabs_controls

### Code 

The code for the flip mount control is largely contained in the following function. The whole file has been included in this Repo for additional context, if necessary.

def Save_Frames(self) :

        self.checkPath()

        flipMount = APTDevice_BayUnit #create flipMount object using APTDevice class from thorlabs_apt_devices lib.

        #Identify mounts seperately using their serial number (found on sticker on device) 
        stageTest = flipMount(serial_number="37869") 
        stageReference = flipMount(serial_number="37868")

        #Open Gates
        if stageReference.status['forward_limit_switch'] == False: #if true- OPEN / if false - CLOSED
            print("Reference gate opening")
            stageReference.move_jog(False) #OPEN flip mount
        else:
            print("Reference gate open")

        if stageTest.status['forward_limit_switch'] == False: #if true- OPEN / if false - CLOSED
            print("Test gate opening")
            stageTest.move_jog(False) #OPEN flip mount
        else: 
            print("Test gate open")

        #Capture Images
        time.sleep(3)
        for i in range (10) :
            im1,im2 = self.getImPair() 
            im1label = 'plate_t{}.npy'.format(i)
            im2label = 'plate_r{}.npy'.format(i)
            np.save(self.path+im1label,im1)
            np.save(self.path+im2label,im2)

        time.sleep(3)
        
        #Movement 
        stageTest.move_jog(True)
        time.sleep(3) #pause in between movements to steadily capture images.
        self.testblockedframesButtonCB()
        time.sleep(3)
        stageTest.move_jog(False)
        time.sleep(3)
        stageReference.move_jog(True)
        time.sleep(3)
        self.refblockedframesButtonCB()
        time.sleep(3)
        stageReference.move_jog(False)

        time.sleep(3)

### Notes

The key call is <em>object_name</em>.move_jog(False) for opening the gate and  <em>object_name</em>.move_jog(True) for closing the gate.

To confirm that the computer recognizes the device, you can blink an LED on the flip mounts(and likely for other ThorLabs devices) by calling <em>object_name</em>.identify()

Contact me at aigriffi@ucsc.edu

