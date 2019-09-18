import config
import pynetbox
import regions as regions
from utilities.slugify import slugify
net_box = pynetbox.api(config.NETBOX_URL, config.TOKEN)


def add_site(name, region):
    backup_region = region
    parent_region_test = 'Magic_Placement'
    region_id = None

    backup_region = net_box.dcim.regions.get(slug=backup_region)
    if backup_region:
        region_id = backup_region.id
    elif not backup_region:
        region = regions.add_regions(region, parent_region_test)
        region_id = region.id

    slug = slugify(name)

    site_info = net_box.dcim.sites.create({"name": name, "slug": slug, "region": region_id})

    print(site_info)
    return site_info
