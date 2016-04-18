Ryu SDN-IP
====

SDN-IP Ryu version

Original SDN-IP is one of project from ONOS.

To use:

Clone Ryu SDN-IP repo
```bash
$ git clone https://github.com/TakeshiTseng/Ryu-SDN-IP.git && cd Ryu-SDN-IP
```

Create config file for Ryu SDN-IP
```bash
cp config.sample.json config.json
```

Configuration file:
```json
{
  "local": {
    "as_number": 65113,  /* SDN-IP AS number */
    "router_id": "192.168.1.10",  /* SDN-IP router id(IP address) */
    "listen_port": 2000  /* listen port */
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

Start Ryu SDN-IP applications:
```bash
$ ryu-manager --observe-links arp_proxy.py fwd_bgp.py sdn_ip.py
```


Reference:
[SDN-IP wiki](https://wiki.onosproject.org/display/ONOS/SDN-IP)
