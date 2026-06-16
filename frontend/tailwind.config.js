import frappeUIPreset from 'frappe-ui/tailwind'

/** @type {import('tailwindcss').Config} */
export default {
  // Single design-token source for the whole suite: the frappe-ui preset
  // supplies the ink/surface/outline color tokens + spacing scale used by all
  // 7 apps. Per-app tailwind configs are dropped in favor of this one.
  presets: [frappeUIPreset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
    '../node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/frappe/components/**/*.{vue,js,ts,jsx,tsx}',
    '../node_modules/frappe-ui/frappe/components/**/*.{vue,js,ts,jsx,tsx}',
  ],
  // Writer/editor dynamic font-size + leading classes are generated at runtime;
  // keep them safelisted so the merged editor ports don't lose styles.
  safelist: [
    'text-[13px]',
    'text-[14px]',
    'text-[15px]',
    'text-[16px]',
    'text-[17px]',
    'text-[18px]',
    'text-[19px]',
    'leading-[1.2]',
    'leading-[1.4]',
    'leading-[1.5]',
    'leading-[1.6]',
    'leading-[1.8]',
    'leading-[2]',
    'leading-[2.2]',
    'leading-[2.5]',
    'leading-[3]',
  ],
  variants: {
    extend: {
      display: ['group-hover'],
    },
  },
}
