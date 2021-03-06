import processor.config as config
import pynetbox
import processor.sites as sites
import processor.regions as regions
import processor.map_devices as map_devices
import re
from processor.utilities.slugify import slugify
from processor.utilities.transliteration import transliterate
from functools import lru_cache

net_box = pynetbox.api(config.NETBOX_URL, config.TOKEN)
parent_region_test = 'Magic_Placement'


def device_name_SWITCH(map_dev, xl_map, region):
    device_role = net_box.dcim.device_roles.get(name='Switch').id
    ip_mask = '/' + region[3].split('/')[-1]
    region = region[1].strip()
    result = []
    region = slugify(region)

    for init in map_dev:

        dev = map_dev[init]

        ip_address = dev.get('address')

        site_arr = xl_map.get(ip_address)

        if (dev.get('description') and site_arr):
            site_arr[3].update({'hint': dev.get('description')})
            desc_tmp = site_arr[3]
            dev['description'] = desc_tmp

        if not site_arr:
            continue
        number_house = re.sub('[,/]', '_', dev.get('name').split()[-1].split('.')[0])
        site_name = (site_arr[0] + ' ' + number_house).strip()
        trans_name = site_arr[2]
        site_name = transliterate(site_name)
        site_info = net_box.dcim.sites.get(name=site_name.strip())
        if not site_info:
            site_info = net_box.dcim.sites.get(slug=slugify(site_name.strip()))
        region_info = net_box.dcim.regions.get(slug=region)

        if not region_info:
            region = regions.add_regions(region, parent_region_test).slug

        if site_info:
            site = site_info
            site_id = site.id
        else:
            site = sites.add_site(trans_name + ' ' + number_house, site_name, region)
            site_id = site.id

        names_regions = []
        region_tmp = region

        while region_tmp:

            name_this_region = net_box.dcim.regions.get(slug=region_tmp)
            names_regions.append(name_this_region.slug)
            region_tmp = name_this_region.parent
            if region_tmp:
                region_tmp = region_tmp.slug

        names_regions = names_regions[-1]

        name_prefix_tmp = dev.get('name').split('.')
        name_prefix_tmp.remove(name_prefix_tmp[0])
        name_prefix = '.'.join(name_prefix_tmp)

        name = '-'.join((names_regions, site.slug))
        if name_prefix:
            name = name + '.' + name_prefix

        name_type_tmp = dev.get('description')['hint'].split('\n')[0]
        name_type = re.sub(r'^\[font .*\]', '', name_type_tmp).split(' ')[0]
        type_dev = net_box.dcim.device_types.get(model='T1-' + name_type)

        if type_dev:
            type_id = type_dev.id
            description = dev.get('description')
            if description['P_REMOVED'] == '1':
                description['P_REMOVED'] = True
            elif description['P_REMOVED'] == '0':
                description['P_REMOVED'] = False
            if description['P_TRANSIT'] == '1':
                description['P_TRANSIT'] = True
            elif description['P_TRANSIT'] == '0':
                description['P_TRANSIT'] = False
            json_dev = {"name": name,
                        "device_type": type_id,
                        "device_role": device_role,
                        "site": site_id,
                        "tags": ["test-0919", ],
                        "comments": description.pop('hint'),
                        "custom_fields": description
                        }

            result.append([json_dev, {
                                        "primary_ip": ip_address + ip_mask,
                                        "addresses": dev.get('addresses'),
                                        }])
        else:
            print('Не установлен Тип в config для данного устройства:', name_type, name, ip_address)

    create_dev = add_devices(result)

    return create_dev


def device_name_MODEM(init_map, region):

    result = []
    device_role = net_box.dcim.device_roles.get(name='SIP').id
    site_id = net_box.dcim.sites.get(name='MODEM_SITE').id
    ip_mask = '/' + net_box.ipam.prefixes.get(site_id=site_id, role='sip').prefix.split('/')[-1]

    for ip, dev in init_map.items():

        type_id = data_dev_hook(dev['model'])

        json_dev = {"name": dev['id'],
                    "device_type": type_id,
                    "device_role": device_role,
                    "site": site_id,
                    "tags": ["test-0919", ],
                    "comments": dev['description'],
                    }

        result.append([json_dev, {
                                "primary_ip": ip + ip_mask,
                                "addresses": dev.get('addresses'),
                                }])

    create_dev = add_devices(result)
    return create_dev


@lru_cache(maxsize=40)
def data_dev_hook(model):

    slug_model = slugify('T1-' + model)
    type_id = net_box.dcim.device_types.get(slug=slug_model).id

    return type_id


def add_devices(json_names):

    create_devices = []

    for name in json_names:
        try:
            dev_id = net_box.dcim.devices.get(name=name[0]['name'])
            if not dev_id:
                created_dev = net_box.dcim.devices.create(name[0])
                created_dev.update(name[1])
                create_devices.append(created_dev)

        except pynetbox.core.query.RequestError as e:

            print(e.error)

    return create_devices


if __name__ == "__main__":
    pass
