Vagrant.configure("2") do |config|
    config.vm.box = "bento/ubuntu-19.04"

    config.vm.define :c_1 do | c_1 |
        c_1.vm.hostname = "c1"
        c_1.vm.network :private_network, ip: "192.168.10.2", virtualbox__intnet: "intnet1sw"
        c_1.vm.provider "virtualbox" do |virtualbox|
            virtualbox.memory = "512"
            virtualbox.cpus = "1"
        end
        c_1.vm.provision "shell", inline: "sudo ip route add 192.168.0.0/16 via 192.168.10.1"
    end

    config.vm.define :c_2 do | c_2 |
        c_2.vm.hostname = "c2"
        c_2.vm.network :private_network, ip: "192.168.20.2", virtualbox__intnet: "intnet2sw"
		c_2.vm.provider "virtualbox" do |virtualbox|
            virtualbox.memory = "512"
			virtualbox.cpus = "1"
        end
        c_2.vm.provision "shell", inline: "sudo ip route add 192.168.0.0/16 via 192.168.20.1"
    end

    config.vm.define :c_3 do | c_3 |
        c_3.vm.hostname = "c3"
        c_3.vm.network :private_network, ip: "192.168.30.2", virtualbox__intnet: "intnet3sw"
        c_3.vm.provider "virtualbox" do |virtualbox|
            virtualbox.memory = "512"
			virtualbox.cpus = "1"
        end
        c_3.vm.provision "shell", inline: "sudo ip route add 192.168.0.0/16 via 192.168.30.1"
    end

    config.vm.define :sw_1 do | sw_1 |
        sw_1.vm.hostname = "sw1"
        sw_1.vm.network :private_network, ip: "192.168.10.1", virtualbox__intnet: "intnet1sw"
        sw_1.vm.network :private_network, ip: "192.168.20.1", virtualbox__intnet: "intnet2sw"
        sw_1.vm.network :private_network, ip: "192.168.30.1", virtualbox__intnet: "intnet3sw"
        sw_1.vm.provider "virtualbox" do |virtualbox|
            virtualbox.memory = "512"
			virtualbox.cpus = "1"
        end
        sw_1.vm.provision "shell", inline: "echo 1 >/proc/sys/net/ipv4/ip_forward"

    end
end
