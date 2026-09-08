import food from "../data/dayz_food.json";
import weapons from "../data/dayz_weapons.json";
import ammo from "../data/dayz_ammo.json";
import magazines from "../data/dayz_magazines.json";
import clothing from "../data/dayz_clothing.json";
import equipment from "../data/dayz_equipment.json";

export function GET() {
  const entries = [
    ...food.map((x: any) => ({
      title: x.title,
      href: `/food/${x.slug}/`,
      sub: `Food · ${x.fields?.energy || "?"} kcal · ${x.fields?.water || "?"} ml`,
      icon: x.icon_file || "",
    })),
    ...weapons.map((x: any) => ({
      title: x.title,
      href: `/weapons/${x.slug}/`,
      sub: `Weapon · ${x.fields?.category || ""}`,
      icon: x.icon_file || "",
    })),
    ...ammo.map((x: any) => ({
      title: x.title,
      href: `/ammo/${x.slug}/`,
      sub: `Ammo · ${x.fields?.healthdmg || "?"} health dmg`,
      icon: x.icon_file || "",
    })),
    ...magazines.map((x: any) => ({
      title: x.title,
      href: `/magazines/${x.slug}/`,
      sub: `Magazine · ${x.fields?.capacity || "?"}`,
      icon: x.icon_file || "",
    })),
    ...clothing.map((x: any) => ({
      title: x.title,
      href: `/clothing/${x.slug}/`,
      sub: `Clothing · ${x.fields?.inventoryslot || ""}`,
      icon: x.icon_file || "",
    })),
    ...equipment.map((x: any) => ({
      title: x.title,
      href: `/equipment/${x.slug}/`,
      sub: `Equipment · ${x.fields?.category || ""}`,
      icon: x.icon_file || "",
    })),
  ].sort((a, b) => a.title.localeCompare(b.title));
  return new Response(JSON.stringify(entries), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
