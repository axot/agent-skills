# Cables and chargers: certification claims and construction

Use this when the user's criteria involve a certification (USB-IF, Intel/Thunderbolt, MFi, PSE, etc.) or a cable's construction, thickness or stiffness.

## Certification claims

Only look for the claim in `#productTitle`, `#feature-bullets` and the spec table. Don't scan the whole page's `innerText`: the sponsored carousels on almost every cable page include Amazon Basics' "USB-IF認証取得" and IVANKY's "インテル認証", so a page-wide scan wrongly marks most products as certified.

A certification that a seller typed into the spec table, with no TID, is still unverified. The real proof is a TID (Test ID) that shows up in usb.org/products for USB-IF, or in the Intel/Thunderbolt certified list for Thunderbolt. If the listing gives no TID, ask the seller for one before calling the product certified.

## Thunderbolt certified list

The official list is `https://www.thunderbolttechnology.net/products?tid=3&field_prod_tb_version_value_many_to_one=tbv4` (`tid=3` means Cable; use `tbv5` for Thunderbolt 5). Plain curl can fetch it. The `field_company_nid` dropdown on that page lists every certified brand, so a brand that isn't in the dropdown has no certified cable. As of October 2026, CIO, MOTTERU, LINKUP, BENFEI and Alvin's were not in it, while Anker, Belkin, CalDigit, Cable Matters, Satechi, OWC, UGREEN and ELECOM were; re-check the dropdown instead of relying on this snapshot. On Amazon, "Thunderbolt 4対応/互換" in a listing does not mean the cable is certified.

## Construction and materials

Before saying a material "isn't published", check the ChargerLAB / 充电头网 teardowns. They cut cables open and list each layer, the wire count and the diameter. Their article pages load in agent-browser, while plain curl and reader-style fetch tools fail on them. To find the article URL, use the YouTube search results page, which gives the exact title, then slugify that title.

Apple's woven USB-C charge cables have a braided fiber outer layer, a TPE jacket, a shielding net, tensile fibers and 6 conductors. They are 3.3 mm thick for 60W 1m (A2795) and 4.6 mm for 240W 2m (A2794). Their softness comes from having few conductors. Any cable that can drive a display carries extra shielded high-speed pairs, so it will be stiffer.
