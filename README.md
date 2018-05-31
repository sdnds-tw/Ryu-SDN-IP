Ryu SDN-IP
====

SDN-IP Ryu version

Original SDN-IP is one of project from [ONOS](http://onosproject.org/).

## Requirement
----

- Ryu v4.1
- networkx 1.11

## Install
----

1. Clone Ryu SDN-IP repo

```bash
$ git clone https://github.com/TakeshiTseng/Ryu-SDN-IP.git && cd Ryu-SDN-IP
```

2. Install dependences

```bash
$ pip install -r requirements.txt
```

3. Create config file for Ryu SDN-IP

```bash
cp config.sample.json config.json
```

Configuration file example:

```js
{
  "local": {
    "as_number": 65113,  /* SDN-IP AS number */
    "router_id": "192.168.1.10",  /* SDN-IP router id(IP address) */
    "listen_port": 2000,  /* listen port */
    "networks": [  /* local as network prefixes */
      "192.168.10.0/24"
    ]
  },
  "speakers": [  /* Internal BGP speakers for SDN-IP */
    {
      "dpid": "00000000000000002",  /* DP that speaker connected */
      "port": 1,  /* Port that speaker connected */
      "speaker_ids" : [  /* Speaker ID from this connection point */
        "192.168.1.11"
      ],
      "mac": "00:00:00:00:01:01"  /* Speaker mac address */
    },
    {
      "dpid": "00000000000000004",
      "port": 1,
      "speaker_ids" : [
        "192.168.1.12"
      ],
      "mac": "00:00:00:00:02:01"
    }
  ]
}
```

4. Start Ryu SDN-IP applications:

```bash
$ ./bin/sdnip-mgr --observe-links sdnip.arp_proxy sdnip.fwd_bgp sdnip.sdn_ip
```

Reference:

[SDN-IP wiki](https://wiki.onosproject.org/display/ONOS/SDN-IP)

TODO:

- [ ] Internal link failure handling
- [ ] Switch failure handling
- [x] Integrate with [DragonKnight](https://github.com/Ryu-Dragon-Knight/Dragon-Knight)
- [ ] Reconfigurable
