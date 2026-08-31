import { commandHistory } from '@/apps/slides/stores/historyMeta'
import { batchCommand, editElementCommand, editSlideCommand } from '@/apps/slides/stores/commands'
import { activeElement, activeElementIds } from '@/apps/slides/stores/element'
import { currentSlide } from '@/apps/slides/stores/slide'

const NO_SNAPSHOT = Symbol('no-snapshot')

const bindProperty = (getTarget, property, buildCommand) => {
	let snapshot = NO_SNAPSHOT

	const set = (value) => {
		const target = getTarget()
		if (target) target[property] = value
	}

	const begin = () => {
		snapshot = getTarget()?.[property]
	}

	const commit = () => {
		if (snapshot === NO_SNAPSHOT) return
		const newValue = getTarget()?.[property]
		if (newValue !== snapshot) {
			commandHistory.execute(buildCommand(snapshot, newValue))
		}
		snapshot = NO_SNAPSHOT
	}

	return { set, begin, commit }
}

export const useElementProperty = (property) =>
	bindProperty(
		() => activeElement.value,
		property,
		(oldValue, newValue) =>
			editElementCommand({
				slideId: currentSlide.value?.clientId,
				elementIds: activeElementIds.value,
				property,
				oldValue,
				newValue,
			}),
	)

export const useSlideProperty = (property) =>
	bindProperty(
		() => currentSlide.value,
		property,
		(oldValue, newValue) =>
			editSlideCommand({
				slideId: currentSlide.value?.clientId,
				property,
				oldValue,
				newValue,
			}),
	)

export const setElementProperty = (property, value) => {
	commandHistory.execute(
		editElementCommand({
			slideId: currentSlide.value.clientId,
			elementIds: activeElementIds.value,
			property,
			oldValue: activeElement.value[property],
			newValue: value,
		}),
	)
}

export const setElementProperties = (changes) => {
	const commands = changes
		.filter((c) => c.oldValue !== c.newValue)
		.map((c) =>
			editElementCommand({
				slideId: currentSlide.value.clientId,
				elementIds: activeElementIds.value,
				property: c.property,
				oldValue: c.oldValue,
				newValue: c.newValue,
			}),
		)
	if (!commands.length) return
	if (commands.length === 1) {
		commandHistory.execute(commands[0])
		return
	}
	commandHistory.execute(
		batchCommand({
			slideId: currentSlide.value.clientId,
			elementIds: activeElementIds.value,
			commands,
		}),
	)
}
