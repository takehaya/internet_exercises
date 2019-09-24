Vagrant.configure("2") do |config|
    config.vm.box = "bento/ubuntu-19.04"

    config.vm.define :c_1 do | c_1 |
        vyos.vm.hostname = "c_1"
        vyos.vm.network :private_network, ip: "192.168.10.1", virtualbox__intnet: "intnet1sw"

    end

    config.vm.define :c_2 do | c_2 |
        vyos.vm.hostname = "c_2"
        vyos.vm.network :private_network, ip: "192.168.20.1", virtualbox__intnet: "intnet2sw"
    end

    config.vm.define :c_3 do | c_3 |
        vyos.vm.hostname = "c_3"
        vyos.vm.network :private_network, ip: "192.168.30.2", virtualbox__intnet: "intnet3sw"
    end

    config.vm.define :sw_1 do | sw_1 |
        vyos.vm.hostname = "sw_1"
        vyos.vm.network :private_network, ip: "192.168.10.1", virtualbox__intnet: "intnet1sw"
        vyos.vm.network :private_network, ip: "192.168.20.1", virtualbox__intnet: "intnet2sw"
        vyos.vm.network :private_network, ip: "192.168.30.1", virtualbox__intnet: "intnet3sw"
    end

end
