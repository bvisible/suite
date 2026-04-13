import { findElement } from '@/stores/element'

export const editElementCommand = ({ slideId, elementIds, property, oldValue, newValue }) => {
	return {
		slideId,
		elementIds,
		debug: `Edit ${property} of element ${elementIds} on slide ${slideId} to ${newValue}`,
		execute(state) {
			elementIds.forEach((elementId) => {
				findElement(state, slideId, elementId)[property] = newValue
			})
		},
		undo(state) {
			elementIds.forEach((elementId) => {
				findElement(state, slideId, elementId)[property] = oldValue
			})
		},
	}
}

export const batchCommand = ({ slideId, elementIds, commands }) => ({
	slideId,
	elementIds,
	debug: 'Batch edit',
	execute: (state) => {
		commands.forEach((c) => c.execute(state))
	},
	undo: (state) => {
		commands
			.slice()
			.reverse()
			.forEach((c) => c.undo(state))
	},
})
