<template>
  <Dialog
    v-model="open"
    :options="{
      title: 'Settings',
    }"
    @close="model = false"
  >
    <template #body-content>
      <Tabs v-model="tabIndex" :tabs>
        <template #tab-panel>
          <div class="overflow-y-auto ps-1 pt-4">
            <Form>
              <template #default="{ dirty, setDirty, error }">
                <h3 class="text-sm font-medium text-ink-gray-7 mb-3">
                  Configuration
                </h3>
                <div class="flex flex-col gap-4 pb-5 pr-5">
                  <div class="space-y-1.5">
                    <FormLabel label="Font Family" />
                    <FontSelect
                      v-model="settings.font_family"
                      variant="subtle"
                      :options="fontOptions"
                    />
                    <div class="text-xs text-ink-gray-5">
                      {{
                        `Choose the default font family for ${
                          tabIndex === 1 ? 'this document' : 'new documents'
                        }.`
                      }}
                    </div>
                  </div>
                  <FormControl
                    v-model="settings.font_size"
                    type="number"
                    label="Font Size"
                    placeholder="Automatic"
                    :description="'Set the font size  of the editor (px).'"
                  />
                  <FormControl
                    v-model="settings.line_height"
                    type="select"
                    label="Line Height"
                    :options="lineHeightOptions"
                    description="Set the line height of the editor."
                  />
                </div>
                <div class="flex flex-col gap-4">
                  <template v-if="tabIndex === 0">
                    <h3 class="text-sm font-medium text-ink-gray-7">
                      Watermark
                    </h3>
                    <FormControl
                      v-model="settings.watermark_text"
                      type="text"
                      label="Text"
                      placeholder="Your company name.."
                      :description="`Set the text for the watermark.`"
                    />
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <FormControl
                        v-model.number="settings.watermark_size"
                        type="number"
                        label="Size"
                        placeholder="40"
                        :min="10"
                        :max="300"
                        :step="5"
                        :description="`Set the watermark text size (px).`"
                        class="w-full"
                      />
                      <FormControl
                        v-model.number="settings.watermark_angle"
                        type="number"
                        label="Angle"
                        placeholder="-45"
                        :min="-180"
                        :max="180"
                        :step="15"
                        :description="`Set the watermark text angle (°).`"
                        class="w-full"
                      />
                    </div>
                  </template>
                  <FormControl
                    v-else
                    v-model="settings.apply_watermark"
                    type="checkbox"
                    label="Apply Watermark to PDF"
                    :description="'Enable this to automatically apply watermark when downloading PDF for this document.'"
                  />
                </div>
                <!-- <FormControl
                  label="Custom Classes"
                  placeholder="font-semibold"
                  v-model="settings.custom_css"
                  description="Any additional classes to apply."
                  type="textarea"
                /> -->
                <div class="mt-2">
                  <div v-if="error" class="text-xs text-ink-red-4">
                    {{ error }}
                  </div>
                  <Button
                    label="Update"
                    variant="solid"
                    class="w-full mt-3"
                    :disabled="!dirty || error"
                    :loading="resource.loading"
                    @click="
                      () => {
                        if (key === 'writer_settings')
                          resource.setValue.submit({ [key]: settings })
                        else
                          resource.updateSettings.submit({
                            data: JSON.stringify(settings),
                          })
                        setDirty(false)
                      }
                    "
                  />
                </div>
              </template>
            </Form>
          </div>
        </template>
      </Tabs>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, ref, reactive, watchEffect } from 'vue'
import { FormControl, Dialog, Tabs, FormLabel } from 'frappe-ui'
import { FONT_FAMILIES, dynamicList } from '@/utils/'
import Form from '@/components/Form.vue'
import FontSelect from './FontSelect.vue'

const open = ref(true)
const model = defineModel()

const props = defineProps({
  docSettings: { required: true, type: Object },
  globalSettings: { required: true, type: Object },
  editable: Boolean,
})
const tabs = dynamicList([
  { label: 'Everywhere', icon: LucideGlobe2 },
  { label: 'This document', icon: LucideFileText },
])
const tabIndex = ref(props.editable ? 1 : 0)

const fontOptions = computed(() =>
  dynamicList([
    {
      label: 'Automatic',
      value: 'global',
      cond: tabIndex.value === 1,
    },
    ...FONT_FAMILIES,
  ]),
)

const lineHeightOptions = computed(() =>
  dynamicList([
    {
      label: 'Automatic',
      value: 'global',
      cond: tabIndex.value === 1,
    },
    { label: '1.2', value: '1.2' },
    { label: '1.4', value: '1.4' },
    { label: '1.5', value: '1.5' },
    { label: '1.6', value: '1.6' },
    { label: '1.8', value: '1.8' },
    { label: '2', value: '2' },
    { label: '2.5', value: '2.2' },
    { label: '2.5', value: '2.5' },
    { label: '3', value: '3' },
  ]),
)

const resource = computed(() =>
  tabIndex.value === 1 ? props.docSettings : props.globalSettings,
)
const key = computed(() =>
  tabIndex.value === 1 ? 'settings' : 'writer_settings',
)

const KEYS = computed(() => [
  'font_family',
  'font_size',
  'line_height',
  ...(tabIndex.value === 0
    ? ['watermark_text', 'watermark_size', 'watermark_angle']
    : ['apply_watermark']),
])

const settings = reactive({})

watchEffect(() => {
  const base = { ...resource.value.doc[key.value] }
  console.log(KEYS.value)
  for (const k of KEYS.value) {
    if (k === 'apply_watermark') {
      settings[k] = base[k] === true
    } else {
      settings[k] = base[k] || 'global'
    }
  }
})
</script>
