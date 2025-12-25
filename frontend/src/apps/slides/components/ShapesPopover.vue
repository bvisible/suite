<template>
	<Popover :placement="'top'">
		<template #target="{ togglePopover }">
			<div class="cursor-pointer rounded p-2 hover:bg-gray-100" @click="togglePopover()">
				<LucideShapes class="size-4 stroke-[1.5]" />
			</div>
		</template>
		<template #body="{ close }">
			<div class="my-3 flex gap-1 rounded-lg bg-white p-1 shadow-xl">
				<Tooltip text="Rectangle" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('rectangle', close)"
					>
						<LucideRectangleHorizontal class="size-4 stroke-[1.5]" />
					</div>
				</Tooltip>

				<Tooltip text="Circle" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('circle', close)"
					>
						<LucideCircle class="size-4 stroke-[1.5]" />
					</div>
				</Tooltip>

				<Tooltip text="Line" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('line', close)"
					>
						<LucideMinus class="size-4 stroke-[1.5]" />
					</div>
				</Tooltip>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { ref } from 'vue'
import { Popover, Tooltip } from 'frappe-ui'

import { addShapeElement } from '@/stores/element'

const addShape = (shapeType, close) => {
	addShapeElement(shapeType)
	close()
}
</script>
