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
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 40 40"
							stroke="currentColor"
							class="h-[40px] w-[40px]"
						>
							<rect x="2" y="7" width="36" height="26" />
						</svg>
					</div>
				</Tooltip>

				<Tooltip text="Rounded Rectangle" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('rounded rectangle', close)"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 40 40"
							stroke="currentColor"
							class="h-[40px] w-[40px]"
						>
							<rect x="2" y="7" width="36" height="26" rx="5" ry="5" />
						</svg>
					</div>
				</Tooltip>

				<Tooltip text="Square" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('square', close)"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 40 40"
							stroke="currentColor"
							class="h-[40px] w-[40px]"
						>
							<rect x="7" y="7" width="26" height="26" />
						</svg>
					</div>
				</Tooltip>

				<Tooltip text="Rounded Square" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('rounded square', close)"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 40 40"
							stroke="currentColor"
							class="h-[40px] w-[40px]"
						>
							<rect x="7" y="7" width="26" height="26" rx="5" ry="5" />
						</svg>
					</div>
				</Tooltip>

				<Tooltip text="Circle" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('circle', close)"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 40 40"
							stroke="currentColor"
							class="h-[40px] w-[40px]"
						>
							<circle cx="20" cy="20" r="15" />
						</svg>
					</div>
				</Tooltip>

				<Tooltip text="Line" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('line', close)"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 40 40"
							stroke="currentColor"
							class="h-[40px] w-[40px]"
						>
							<line x1="4" y1="20" x2="36" y2="20" />
						</svg>
					</div>
				</Tooltip>

				<Tooltip text="Line with Arrows" :hover-delay="0.6">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="addShape('line with arrows', close)"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 40 40"
							stroke="currentColor"
							class="h-[40px] w-[40px]"
						>
							<defs>
								<marker
									id="arrowLeft"
									markerWidth="6"
									markerHeight="6"
									refX="6"
									refY="3"
									orient="auto"
								>
									<path d="M6,0 L0,3 L6,6 Z" fill="currentColor" stroke="none" />
								</marker>
								<marker
									id="arrowRight"
									markerWidth="6"
									markerHeight="6"
									refX="0"
									refY="3"
									orient="auto"
								>
									<path d="M0,0 L6,3 L0,6 Z" fill="currentColor" stroke="none" />
								</marker>
							</defs>
							<line
								x1="10"
								y1="20"
								x2="30"
								y2="20"
								marker-start="url(#arrowLeft)"
								marker-end="url(#arrowRight)"
							/>
						</svg>
					</div>
				</Tooltip>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { ref } from 'vue'
import { Popover, Tooltip } from 'frappe-ui'

import { addShapeElement } from '@/apps/slides/stores/element'

const addShape = (shapeType, close) => {
	addShapeElement(shapeType)
	close()
}
</script>
